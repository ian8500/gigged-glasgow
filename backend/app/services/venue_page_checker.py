from __future__ import annotations

import re
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib import robotparser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from dateutil.parser import parse as parse_datetime
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.city import City
from app.models.artist import Artist
from app.models.event import Event
from app.models.source import Source
from app.models.venue import Venue
from app.models.venue_check_log import VenueCheckLog
from app.services.normalization import confidence_score, ensure_aware, event_fingerprint, event_slug
from app.sources.base import NormalizedSourceEvent
from app.sources.feed import parse_ical_events, parse_rss_events
from app.sources.structured_data import extract_json_ld_events, extract_microdata_events

USER_AGENT = "GiggedGlasgowVenuePageChecker/1.0 (+https://giggedglasgow.example; editorial review)"
MAX_BYTES = 500_000
REQUEST_TIMEOUT_SECONDS = 8
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 0.5
LOW_CONFIDENCE_THRESHOLD = 0.7
BLOCKED_SOURCE_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "dice.fm",
    "ra.co",
    "residentadvisor.net",
    "skiddle.com",
    "eventbrite.co.uk",
    "eventbrite.com",
}
LOGIN_PATH_MARKERS = ("/login", "/signin", "/sign-in", "/account", "/users/sign_in")


@dataclass(slots=True)
class FetchResponse:
    ok: bool
    url: str
    status_code: int | None = None
    content_type: str | None = None
    body: str = ""
    error: str | None = None


@dataclass(slots=True)
class VenuePageCheckReport:
    venue_id: int
    venue_name: str
    status: str
    coverage_status: str
    coverage_type: str
    source_url: str | None
    confidence_score: float
    events_found: int
    events_created: int
    events_updated: int
    duplicates_skipped: int
    message: str
    robots_checked: bool
    robots_allowed: bool | None
    structure_changed: bool
    diagnostic_summary: dict[str, Any] = field(default_factory=dict)


def check_venue_page(db: Session, venue_id: int) -> VenuePageCheckReport:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise ValueError("Venue not found")

    now = datetime.utcnow()
    diagnostics: dict[str, Any] = {
        "ethical_limits": [
            "Configured official venue sources only.",
            "No social pages, ticketing marketplace page scraping, login, paywall, CAPTCHA, anti-bot or robots.txt bypass.",
            "No browser automation.",
            "No full page HTML is stored.",
        ],
        "parser_counts": {},
        "sample_titles": [],
    }
    report = _empty_report(venue, now, diagnostics)

    if venue.source_mode in {"manual_only", "unsupported", "api"}:
        message = f"Venue source mode is {venue.source_mode}; automated venue page check skipped."
        return _record_report(db, venue, report, now, message, status="needs_review")

    source_url = _configured_source_url(venue)
    feed_url = venue.feed_url
    if not source_url and not feed_url:
        return _record_report(
            db,
            venue,
            report,
            now,
            "No official_events_url or feed_url is configured for this venue.",
            status="needs_review",
        )

    source_to_check = feed_url if venue.source_mode == "feed" and feed_url else source_url
    if source_to_check and source_is_blocked(source_to_check):
        report.source_url = source_to_check
        report.coverage_type = "unsupported"
        report.coverage_status = "unsupported"
        report.confidence_score = 0.1
        report.structure_changed = False
        return _record_report(
            db,
            venue,
            report,
            now,
            "Configured source is unsupported by policy; use an official venue API/feed/page instead.",
            status="needs_review",
        )

    checked_url = source_to_check or source_url
    allowed, robots_message = robots_allows(checked_url) if checked_url else (False, "No URL to check.")
    report.robots_checked = checked_url is not None
    report.robots_allowed = allowed
    diagnostics["robots_message"] = robots_message
    if not allowed:
        report.source_url = checked_url
        report.coverage_type = "unsupported"
        report.coverage_status = "unsupported"
        report.confidence_score = 0.15
        return _record_report(db, venue, report, now, robots_message, status="needs_review")

    events: list[NormalizedSourceEvent] = []
    fetches: list[FetchResponse] = []
    page_fetch: FetchResponse | None = None
    if source_url and venue.source_mode != "feed":
        page_fetch = fetch_public_url(source_url, accept="text/html,application/xhtml+xml")
        fetches.append(page_fetch)
        diagnostics["page"] = _fetch_summary(page_fetch)
        if page_fetch.ok:
            page_events, page_diagnostics = parse_official_page(page_fetch.body, source_url, venue)
            events.extend(page_events)
            diagnostics.update(page_diagnostics)
            if not feed_url:
                embedded_feed = _first_same_origin_feed(source_url, page_diagnostics.get("feed_links", []))
                if embedded_feed:
                    venue.feed_url = embedded_feed
                    diagnostics["embedded_feed_stored"] = embedded_feed
        else:
            report.structure_changed = page_fetch.status_code in {404, 410}

    if feed_url:
        feed_fetch = fetch_public_url(feed_url, accept="application/rss+xml,application/atom+xml,text/calendar,text/plain,*/*")
        fetches.append(feed_fetch)
        diagnostics["feed"] = _fetch_summary(feed_fetch)
        if feed_fetch.ok:
            feed_type = infer_feed_type(feed_url, feed_fetch.content_type, feed_fetch.body)
            feed_events = parse_ical_events(feed_fetch.body, "Official venue feed", feed_url) if feed_type == "ical" else parse_rss_events(feed_fetch.body, "Official venue feed", feed_url)
            diagnostics["parser_counts"]["feed"] = len(feed_events)
            events.extend(feed_events)

    if not any(fetch.ok for fetch in fetches):
        error = next((fetch.error for fetch in fetches if fetch.error), "Configured source could not be fetched.")
        report.source_url = checked_url
        report.coverage_type = "broken"
        report.coverage_status = "broken"
        report.confidence_score = 0.2
        return _record_report(db, venue, report, now, error, status="broken")

    unique_events = dedupe_source_events(events)
    outcomes = upsert_review_events(db, venue, unique_events)
    report.source_url = checked_url
    report.events_found = len(unique_events)
    report.events_created = outcomes["created"]
    report.events_updated = outcomes["updated"]
    report.duplicates_skipped = outcomes["duplicates"]
    report.confidence_score = check_confidence(unique_events, diagnostics)
    report.coverage_type = coverage_type_for(venue, diagnostics)
    report.coverage_status = "automated" if unique_events else "needs_review"
    report.status = "working" if unique_events else "needs_review"
    report.structure_changed = report.structure_changed or (
        bool(source_url) and not unique_events and not diagnostics["parser_counts"].get("json_ld")
    )
    diagnostics["sample_titles"] = [event.title for event in unique_events[:5]]
    diagnostics["events_created"] = outcomes["created"]
    diagnostics["events_updated"] = outcomes["updated"]
    diagnostics["duplicates_skipped"] = outcomes["duplicates"]
    message = (
        f"Found {len(unique_events)} event candidates; all were added to review."
        if unique_events
        else "Source fetched but no supported event data was found; manual review needed."
    )
    return _record_report(db, venue, report, now, message, status=report.status)


def parse_official_page(html: str, source_url: str, venue: Venue) -> tuple[list[NormalizedSourceEvent], dict[str, Any]]:
    json_ld = extract_json_ld_events(html, "Official venue page", source_url)
    microdata = extract_microdata_events(html, "Official venue page", source_url)
    selector_events: list[NormalizedSourceEvent] = []
    selector_enabled = bool(venue.selector_config)
    if selector_enabled:
        selector_events = parse_selector_events(html, source_url, venue)
    feed_links = discover_feed_links(html, source_url)
    diagnostics = {
        "parser_counts": {
            "json_ld": len(json_ld),
            "microdata": len(microdata),
            "selector": len(selector_events),
        },
        "feed_links": feed_links,
        "selector_enabled": selector_enabled,
        "body_bytes_read": len(html.encode("utf-8")),
    }
    return json_ld + microdata + selector_events, diagnostics


def dedupe_source_events(events: list[NormalizedSourceEvent]) -> list[NormalizedSourceEvent]:
    seen: set[str] = set()
    unique: list[NormalizedSourceEvent] = []
    for event in events:
        event.starts_at = ensure_aware(event.starts_at)
        key = event.source_event_id or f"{slugify(event.title)}:{event.starts_at.isoformat()}:{slugify(event.venue_name)}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def upsert_review_events(db: Session, venue: Venue, events: list[NormalizedSourceEvent]) -> dict[str, int]:
    city = db.get(City, venue.city_id)
    if city is None:
        raise ValueError("Venue city not found")
    source = ensure_checker_source(db)
    source.is_enabled = True
    source.current_mode = "structured_data"
    source.automation_allowed = "robots_checked"
    source.terms_reviewed = False
    source.limitations = "Configured official venue pages/feeds only; all extracted events require editorial review."

    outcomes = {"created": 0, "updated": 0, "duplicates": 0}
    for source_event in events:
        source_event.venue_name = venue.name
        if not source_event.artist_name:
            source_event.artist_name = source_event.title
        source_event.starts_at = ensure_aware(source_event.starts_at)
        fingerprint = event_fingerprint(city.slug, source_event)
        existing = None
        if source_event.source_event_id:
            existing = db.scalar(
                select(Event).where(
                    Event.city_id == city.id,
                    Event.source_id == source.id,
                    Event.source_event_id == source_event.source_event_id,
                )
            )
        fingerprint_match = db.scalar(
            select(Event).where(Event.city_id == city.id, Event.normalized_fingerprint == fingerprint)
        )
        if existing is not None and fingerprint_match is not None and existing.id != fingerprint_match.id:
            outcomes["duplicates"] += 1
            continue
        event = existing or fingerprint_match
        created = event is None
        if event is None:
            event = Event(
                city_id=city.id,
                venue_id=venue.id,
                normalized_fingerprint=fingerprint,
                slug=event_slug(source_event.title, source_event.starts_at),
                title=source_event.title,
                starts_at=source_event.starts_at,
            )
            db.add(event)

        artist = find_or_create_artist(db, source_event.artist_name or source_event.title)
        score = confidence_score(source_event, venue.is_whitelisted)
        event.venue_id = venue.id
        event.artist_id = artist.id
        event.source_id = source.id
        event.title = source_event.title
        event.description = source_event.description
        event.slug = event_slug(source_event.title, source_event.starts_at)
        event.starts_at = source_event.starts_at
        event.ends_at = source_event.ends_at
        event.ticket_url = source_event.ticket_url
        event.source_url = source_event.source_url or source_event.ticket_url
        event.image_url = source_event.image_url
        event.venue_address = source_event.venue_address or venue.address
        event.venue_postcode = source_event.venue_postcode or venue.postcode
        event.price_min = source_event.price_min
        event.price_max = source_event.price_max
        event.currency = source_event.currency
        event.genre = source_event.genre
        event.status = "scheduled"
        event.confidence_score = score
        event.source_event_id = source_event.source_event_id
        event.source_attribution = "Official venue page checker"
        event.needs_review = True
        event.raw_payload = {
            "source_kind": source_event.source_kind,
            "source_url": source_event.source_url,
            "confidence_hints": source_event.confidence_hints,
            "low_confidence": score < LOW_CONFIDENCE_THRESHOLD,
            "payload": source_event.raw_payload,
        }
        outcomes["created" if created else "updated"] += 1
    return outcomes


def ensure_checker_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == "Official venue page checker"))
    if source is None:
        source = Source(
            name="Official venue page checker",
            slug="official-venue-page-checker",
            kind="venue_page",
            is_enabled=True,
        )
        db.add(source)
        db.flush()
    return source


def find_or_create_artist(db: Session, name: str) -> Artist:
    slug = slugify(name)
    artist = db.scalar(select(Artist).where(Artist.slug == slug))
    if artist is None:
        artist = Artist(name=name, slug=slug)
        db.add(artist)
        db.flush()
    return artist


def source_is_blocked(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if any(host == domain or host.endswith(f".{domain}") for domain in BLOCKED_SOURCE_DOMAINS):
        return True
    return any(marker in parsed.path.lower() for marker in LOGIN_PATH_MARKERS)


def robots_allows(url: str | None) -> tuple[bool, str]:
    if not url:
        return False, "No URL configured."
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False, "Invalid URL; manual review required."
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            robots_body = response.read(MAX_BYTES).decode("utf-8", errors="ignore").splitlines()
        parser.parse(robots_body)
    except (OSError, URLError, socket.timeout):
        return True, "robots.txt could not be read; proceeding with a single lightweight public-source check."
    if not parser.can_fetch(USER_AGENT, url):
        return False, "robots.txt disallows automated checks for this configured URL."
    return True, "robots.txt permits this configured URL."


def fetch_public_url(url: str, accept: str = "*/*") -> FetchResponse:
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    last_error: str | None = None
    for attempt in range(MAX_ATTEMPTS):
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                status_code = int(getattr(response, "status", 200))
                content_type = response.headers.get("content-type", "")
                body = response.read(MAX_BYTES).decode("utf-8", errors="ignore")
            return FetchResponse(
                ok=200 <= status_code < 400,
                url=url,
                status_code=status_code,
                content_type=content_type,
                body=body,
            )
        except HTTPError as exc:
            return FetchResponse(
                ok=False,
                url=url,
                status_code=exc.code,
                error=f"Configured source returned HTTP {exc.code}.",
            )
        except (OSError, URLError, socket.timeout) as exc:
            last_error = f"Configured source request failed: {exc.__class__.__name__}."
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)
    return FetchResponse(ok=False, url=url, error=last_error or "Configured source request failed.")


def discover_feed_links(html: str, source_url: str) -> list[str]:
    parser = _FeedLinkParser(source_url)
    parser.feed(html)
    return parser.links


def parse_selector_events(html: str, source_url: str, venue: Venue) -> list[NormalizedSourceEvent]:
    config = venue.selector_config or {}
    required = {"event_container", "title", "starts_at"}
    if not required.issubset(config):
        return []
    blocks = _select_blocks(html, str(config["event_container"]))
    events: list[NormalizedSourceEvent] = []
    for block in blocks[:50]:
        title = _select_text(block, str(config["title"]))
        date_value = _select_text(block, str(config["starts_at"]))
        if not title or not date_value:
            continue
        try:
            starts_at = parse_datetime(date_value)
        except (TypeError, ValueError):
            continue
        ticket = _select_attr(block, str(config.get("ticket_url") or ""), "href")
        image = _select_attr(block, str(config.get("image") or ""), "src")
        price_text = _select_text(block, str(config.get("price") or ""))
        events.append(
            NormalizedSourceEvent(
                title=title,
                artist_name=title,
                venue_name=venue.name,
                starts_at=starts_at,
                ticket_url=urljoin(source_url, ticket) if ticket else source_url,
                source_url=urljoin(source_url, ticket) if ticket else source_url,
                image_url=urljoin(source_url, image) if image else None,
                source_name="Official venue page selector",
                source_kind="selector",
                source_event_id=f"{source_url}#{slugify(title)}-{starts_at.date().isoformat()}",
                source_attribution="Official venue page checker",
                raw_payload={"title": title, "starts_at": date_value, "price": price_text},
                confidence_hints={
                    "has_source_id": True,
                    "has_ticket_url": bool(ticket),
                    "has_artist": False,
                    "has_venue": True,
                    "has_datetime": True,
                },
            )
        )
    return events


def infer_feed_type(feed_url: str, content_type: str | None, body: str) -> str:
    lowered = f"{feed_url} {content_type or ''} {body[:80]}".lower()
    return "ical" if "text/calendar" in lowered or "begin:vcalendar" in lowered or ".ics" in lowered else "rss"


def check_confidence(events: list[NormalizedSourceEvent], diagnostics: dict[str, Any]) -> float:
    if not events:
        return 0.45 if any(count for count in diagnostics.get("parser_counts", {}).values()) else 0.35
    scores = []
    for event in events:
        hints = event.confidence_hints
        present = sum(1 for value in hints.values() if value)
        scores.append(0.45 + min(0.45, present * 0.09))
    return min(0.95, max(scores))


def coverage_type_for(venue: Venue, diagnostics: dict[str, Any]) -> str:
    if venue.source_mode == "feed" or diagnostics.get("parser_counts", {}).get("feed"):
        return "feed"
    if diagnostics.get("parser_counts", {}).get("selector"):
        return "selector"
    if diagnostics.get("parser_counts", {}).get("json_ld") or diagnostics.get("parser_counts", {}).get("microdata"):
        return "structured_data"
    return "website"


def _configured_source_url(venue: Venue) -> str | None:
    return venue.official_events_url


def _empty_report(venue: Venue, now: datetime, diagnostics: dict[str, Any]) -> VenuePageCheckReport:
    return VenuePageCheckReport(
        venue_id=venue.id,
        venue_name=venue.name,
        status="needs_review",
        coverage_status=venue.coverage_status or "manual_only",
        coverage_type="manual",
        source_url=venue.official_events_url or venue.feed_url,
        confidence_score=venue.confidence_score or 0.5,
        events_found=0,
        events_created=0,
        events_updated=0,
        duplicates_skipped=0,
        message="Venue check pending.",
        robots_checked=False,
        robots_allowed=venue.robots_allowed,
        structure_changed=False,
        diagnostic_summary=diagnostics,
    )


def _record_report(
    db: Session,
    venue: Venue,
    report: VenuePageCheckReport,
    now: datetime,
    message: str,
    status: str,
) -> VenuePageCheckReport:
    report.message = message
    venue.last_checked_at = now
    venue.robots_allowed = report.robots_allowed
    venue.structure_changed = report.structure_changed
    venue.confidence_score = report.confidence_score
    venue.last_error = message if status in {"broken", "needs_review"} and report.coverage_status in {"broken", "unsupported"} else None
    if report.events_found:
        venue.last_success_at = now
        venue.last_event_found_at = now
        venue.last_error = None
        venue.structured_data_supported = report.coverage_type in {"structured_data", "selector"}
    if report.coverage_status:
        venue.coverage_status = report.coverage_status

    db.add(
        VenueCheckLog(
            venue_id=venue.id,
            checked_at=now,
            status=status,
            coverage_status=report.coverage_status,
            confidence_score=report.confidence_score,
            events_found=report.events_found,
            official_events_url=report.source_url,
            supported_sources=report.coverage_type,
            robots_checked=report.robots_checked,
            structure_changed=report.structure_changed,
            message=message,
            raw_payload=report.diagnostic_summary,
        )
    )
    db.commit()
    report.diagnostic_summary = _safe_diagnostics(report.diagnostic_summary)
    return report


def _fetch_summary(fetch: FetchResponse) -> dict[str, Any]:
    return {
        "ok": fetch.ok,
        "status_code": fetch.status_code,
        "content_type": fetch.content_type,
        "bytes_read": len(fetch.body.encode("utf-8")),
        "error": fetch.error,
    }


def _safe_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    safe = dict(diagnostics)
    safe.pop("html", None)
    return safe


def _first_same_origin_feed(source_url: str, links: list[str]) -> str | None:
    parsed_source = urlparse(source_url)
    for link in links:
        parsed = urlparse(link)
        if parsed.netloc == parsed_source.netloc:
            return link
    return None


class _FeedLinkParser(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        attributes = {key.lower(): value or "" for key, value in attrs}
        rel = attributes.get("rel", "").lower()
        mime = attributes.get("type", "").lower()
        href = attributes.get("href")
        if href and "alternate" in rel and any(token in mime for token in ("rss", "atom", "calendar", "ical")):
            self.links.append(urljoin(self.source_url, href))


def _select_blocks(html: str, selector: str) -> list[str]:
    if not selector:
        return []
    if selector.startswith("."):
        class_name = re.escape(selector[1:])
        pattern = rf"<(?P<tag>[a-z0-9]+)[^>]*class=[\"'][^\"']*\b{class_name}\b[^\"']*[\"'][^>]*>.*?</(?P=tag)>"
    elif selector.startswith("#"):
        element_id = re.escape(selector[1:])
        pattern = rf"<(?P<tag>[a-z0-9]+)[^>]*id=[\"']{element_id}[\"'][^>]*>.*?</(?P=tag)>"
    else:
        tag = re.escape(selector)
        pattern = rf"<{tag}[^>]*>.*?</{tag}>"
    return re.findall(pattern, html, flags=re.IGNORECASE | re.DOTALL) if "(?P<tag>" not in pattern else [
        match.group(0) for match in re.finditer(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    ]


def _select_text(html: str, selector: str) -> str | None:
    block = next(iter(_select_blocks(html, selector)), None)
    if not block:
        return None
    return re.sub(r"<[^>]+>", " ", block).strip()


def _select_attr(html: str, selector: str, attr: str) -> str | None:
    block = next(iter(_select_blocks(html, selector)), None)
    if not block:
        return None
    match = re.search(rf"\b{re.escape(attr)}=[\"']([^\"']+)[\"']", block, flags=re.IGNORECASE)
    return match.group(1) if match else None
