from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

from dateutil import parser as date_parser
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models.city import City
from app.models.event import Event
from app.models.extracted_event_candidate import ExtractedEventCandidate
from app.models.scrape_run import ScrapeRun
from app.models.source import Source
from app.models.venue import Venue
from app.services.ingestion import find_or_create_artist
from app.services.normalization import event_slug, fingerprint_parts

USER_AGENT = "GiggedGlasgowBot/0.1 (+https://giggedglasgow.local; official venue page checker)"
TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 1_000_000

UNSUPPORTED_HOST_PARTS = {
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "eventbrite.",
    "skiddle.com",
    "dice.fm",
    "ra.co",
    "residentadvisor.net",
}


@dataclass
class FetchResponse:
    ok: bool
    url: str
    status_code: int | None = None
    content_type: str | None = None
    body: str = ""
    error: str | None = None


@dataclass
class CandidateData:
    venue_id: int | None = None
    city_slug: str = "glasgow"
    source_url: str | None = None
    source_type: str = "structured_data"
    raw_title: str | None = None
    title: str = ""
    artist: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    price_text: str | None = None
    ticket_url: str | None = None
    image_url: str | None = None
    description: str | None = None
    confidence_score: float = 0.4
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapeResult:
    venue_id: int
    venue_name: str
    status: str
    events_found: int = 0
    candidates_created: int = 0
    duplicates: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run_city_scrape(city_slug: str = "glasgow", db: Session | None = None) -> dict[str, Any]:
    owns_session = db is None
    db = db or SessionLocal()
    run = ScrapeRun(city_slug=city_slug, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    errors: list[str] = []
    warnings: list[str] = []
    try:
        city = db.scalar(select(City).where(City.slug == city_slug))
        if city is None:
            raise ValueError(f"City not found: {city_slug}")
        venues = list(
            db.scalars(
                select(Venue)
                .where(Venue.city_id == city.id, Venue.status != "duplicate")
                .order_by(Venue.name)
            )
        )
        for venue in venues:
            result = scrape_venue(venue.id, db=db)
            run.venues_checked += 1
            run.events_found += result.events_found
            run.events_created += result.candidates_created
            run.events_needing_review += result.candidates_created
            errors.extend(f"{result.venue_name}: {error}" for error in result.errors)
            warnings.extend(f"{result.venue_name}: {warning}" for warning in result.warnings)
        run.status = "completed_with_errors" if errors else "completed"
    except Exception as exc:  # pragma: no cover - defensive run accounting
        run.status = "failed"
        errors.append(str(exc))
    finally:
        run.finished_at = datetime.utcnow()
        run.errors = "\n".join(errors) if errors else None
        run.warnings = "\n".join(warnings) if warnings else None
        db.commit()
        db.refresh(run)
        payload = scrape_run_payload(run)
        if owns_session:
            db.close()
    return payload


def scrape_venue(venue_id: int, db: Session | None = None) -> ScrapeResult:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        venue = db.get(Venue, venue_id)
        if venue is None:
            raise ValueError(f"Venue not found: {venue_id}")
        result = ScrapeResult(venue_id=venue.id, venue_name=venue.name, status="checked")
        venue.last_checked_at = datetime.utcnow()

        source_mode = venue.source_mode or "manual_only"
        if source_mode == "manual_only":
            result.status = "manual_only"
            result.warnings.append("Venue is marked manual-only.")
            update_venue_status(venue, "manual_only", "Manual-only venue; skipped auto finder.")
            db.commit()
            return result

        if source_mode == "unsupported":
            result.status = "unsupported"
            result.warnings.append("Venue is marked unsupported.")
            update_venue_status(venue, "unsupported", "Unsupported venue source; skipped auto finder.")
            db.commit()
            return result

        primary_url = venue.event_listings_url or venue.official_events_url or venue.feed_url
        if not primary_url:
            result.status = "missing_url"
            result.warnings.append("No official event page or feed URL configured.")
            update_venue_status(venue, "missing_url", "No official event page or feed URL configured.")
            db.commit()
            return result

        if is_unsupported_url(primary_url):
            result.status = "unsupported"
            result.warnings.append(f"Skipped unsupported source: {primary_url}")
            venue.robots_allowed = False
            update_venue_status(venue, "unsupported", f"Skipped unsupported source: {primary_url}")
            db.commit()
            return result

        allowed, robots_note = robots_allowed(primary_url)
        venue.robots_allowed = allowed
        if not allowed:
            result.status = "robots_blocked"
            result.warnings.append(robots_note)
            update_venue_status(venue, "robots_blocked", robots_note)
            db.commit()
            return result

        candidates: list[CandidateData] = []
        if source_mode in {"rss", "feed"} or looks_like_feed(primary_url):
            candidates.extend(extract_rss_or_atom_events(primary_url))
        elif source_mode == "ical" or looks_like_ical(primary_url):
            candidates.extend(extract_ical_events(primary_url))
        else:
            response = fetch_public_page(primary_url)
            if not response.ok:
                result.status = "broken"
                result.errors.append(response.error or "Could not fetch configured venue page.")
                update_venue_status(venue, "broken", response.error or "Could not fetch configured venue page.")
                db.commit()
                return result

            candidates.extend(extract_json_ld_events(response.body, response.url))
            for feed_url in discover_feed_links(response.body, response.url):
                if robots_allowed(feed_url)[0]:
                    candidates.extend(extract_rss_or_atom_events(feed_url))
            for ical_url in discover_ical_links(response.body, response.url):
                if robots_allowed(ical_url)[0]:
                    candidates.extend(extract_ical_events(ical_url))
            selector_config = venue.scraper_selector_config or venue.selector_config
            if source_mode == "selector" and selector_config:
                candidates.extend(extract_with_selector_config(response.body, selector_config, response.url))
            elif source_mode == "selector":
                result.warnings.append("Selector mode is enabled but no selector config is set.")

        seen = set()
        for candidate in candidates:
            candidate.venue_id = venue.id
            candidate.city_slug = venue.city.slug
            candidate = normalise_candidate(candidate)
            if not candidate.title or not candidate.starts_at:
                result.warnings.append(f"Skipped incomplete candidate from {candidate.source_url or primary_url}.")
                continue
            local_key = candidate_key(candidate)
            if local_key in seen:
                result.duplicates += 1
                continue
            seen.add(local_key)
            stored = store_candidate(db, venue, candidate)
            result.events_found += 1
            if stored.status == "duplicate":
                result.duplicates += 1
            else:
                result.candidates_created += 1

        if result.events_found:
            venue.last_event_found_at = datetime.utcnow()
            venue.last_success_at = datetime.utcnow()
            update_venue_status(venue, "ok", f"Found {result.events_found} possible gigs.")
        else:
            update_venue_status(venue, "no_events_found", "Checked safely; no possible gigs found.")
        db.commit()
        return result
    finally:
        if owns_session:
            db.close()


def fetch_public_page(url: str) -> FetchResponse:
    if is_unsupported_url(url):
        return FetchResponse(ok=False, url=url, error=f"Unsupported source skipped: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status_code = getattr(response, "status", None)
            content_type = response.headers.get("content-type")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                return FetchResponse(ok=False, url=url, status_code=status_code, content_type=content_type, error="Response too large; skipped.")
            charset = response.headers.get_content_charset() or "utf-8"
            return FetchResponse(
                ok=bool(status_code is None or 200 <= status_code < 300),
                url=response.geturl(),
                status_code=status_code,
                content_type=content_type,
                body=raw.decode(charset, errors="replace"),
            )
    except urllib.error.HTTPError as exc:
        return FetchResponse(ok=False, url=url, status_code=exc.code, error=f"Configured source returned HTTP {exc.code}.")
    except Exception as exc:
        return FetchResponse(ok=False, url=url, error=f"Could not fetch configured source: {exc}")


def robots_allowed(url: str) -> tuple[bool, str]:
    if is_unsupported_url(url):
        return False, f"Unsupported source skipped: {url}"
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False, "Invalid URL."
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return True, "robots.txt unavailable; continuing with a single polite request to the configured venue URL."
    allowed = parser.can_fetch(USER_AGENT, url)
    if not allowed:
        return False, "robots.txt disallows automated checks for this configured URL."
    return True, "robots.txt allows this configured URL."


def extract_json_ld_events(html: str, source_url: str) -> list[CandidateData]:
    parser = JsonLdParser()
    parser.feed(html)
    candidates: list[CandidateData] = []
    for raw_script in parser.scripts:
        try:
            payload = json.loads(raw_script)
        except json.JSONDecodeError:
            continue
        for event in iter_schema_events(payload):
            candidates.append(candidate_from_json_ld(event, source_url))
    return candidates


def extract_rss_or_atom_events(feed_url: str) -> list[CandidateData]:
    response = fetch_public_page(feed_url)
    if not response.ok:
        return []
    return parse_rss_or_atom(response.body, response.url)


def extract_ical_events(feed_url: str) -> list[CandidateData]:
    response = fetch_public_page(feed_url)
    if not response.ok:
        return []
    return parse_ical_text(response.body, response.url)


def extract_with_selector_config(
    html: str,
    config: dict[str, Any],
    source_url: str | None = None,
) -> list[CandidateData]:
    tree = HtmlTreeParser()
    tree.feed(html)
    cards = find_all(tree.root, str(config.get("event_card") or ""))
    candidates: list[CandidateData] = []
    for card in cards:
        title = text_for_selector(card, config.get("title"))
        date_text = text_for_selector(card, config.get("date"))
        if not title or not date_text:
            continue
        candidates.append(
            CandidateData(
                source_url=source_url,
                source_type="selector",
                raw_title=title,
                title=title,
                starts_at=parse_datetime(date_text),
                ticket_url=url_for_selector(card, config.get("ticket_url"), source_url),
                image_url=url_for_selector(card, config.get("image_url"), source_url, attr="src"),
                confidence_score=0.55,
                raw_payload={"selector_config_keys": sorted(config.keys()), "date_text": date_text},
            )
        )
    return candidates


def normalise_candidate(candidate: CandidateData) -> CandidateData:
    candidate.title = clean_text(candidate.title or candidate.raw_title or "")
    candidate.raw_title = candidate.raw_title or candidate.title
    if isinstance(candidate.starts_at, str):
        candidate.starts_at = parse_datetime(candidate.starts_at)
    score = 0.25
    score += 0.25 if candidate.title else 0
    score += 0.25 if candidate.starts_at else 0
    score += 0.1 if candidate.ticket_url else 0
    score += 0.1 if candidate.source_url else 0
    score += 0.05 if candidate.image_url else 0
    if candidate.source_type == "structured_data":
        score += 0.1
    candidate.confidence_score = min(round(max(candidate.confidence_score, score), 2), 1.0)
    return candidate


def dedupe_candidate(candidate: CandidateData, db: Session | None = None) -> tuple[bool, int | None]:
    if db is None or candidate.starts_at is None or candidate.venue_id is None:
        return False, None
    statement = select(Event).where(Event.venue_id == candidate.venue_id)
    if candidate.source_url or candidate.ticket_url:
        statement = statement.where(
            or_(
                Event.source_url == candidate.source_url,
                Event.ticket_url == candidate.ticket_url,
            )
        )
        existing = db.scalar(statement)
        if existing:
            return True, existing.id
    date_start = candidate.starts_at.date()
    for event in db.scalars(select(Event).where(Event.venue_id == candidate.venue_id)):
        if event.starts_at and event.starts_at.date() == date_start:
            title_similarity = SequenceMatcher(None, clean_text(event.title).lower(), candidate.title.lower()).ratio()
            if title_similarity >= 0.82:
                return True, event.id
    existing_candidate = db.scalar(
        select(ExtractedEventCandidate).where(
            ExtractedEventCandidate.venue_id == candidate.venue_id,
            ExtractedEventCandidate.title == candidate.title,
            ExtractedEventCandidate.starts_at == candidate.starts_at,
        )
    )
    if existing_candidate:
        return True, existing_candidate.existing_event_id
    return False, None


def approve_candidate(db: Session, candidate_id: int) -> ExtractedEventCandidate:
    candidate = require_candidate(db, candidate_id)
    if candidate.status != "duplicate":
        candidate.status = "approved"
    db.commit()
    db.refresh(candidate)
    return candidate


def reject_candidate(db: Session, candidate_id: int) -> ExtractedEventCandidate:
    candidate = require_candidate(db, candidate_id)
    candidate.status = "rejected"
    db.commit()
    db.refresh(candidate)
    return candidate


def convert_candidate_to_event(db: Session, candidate_id: int) -> Event:
    candidate = require_candidate(db, candidate_id)
    if candidate.status == "duplicate" and candidate.existing_event_id:
        existing = db.get(Event, candidate.existing_event_id)
        if existing is not None:
            return existing
    venue = db.get(Venue, candidate.venue_id)
    city = db.scalar(select(City).where(City.slug == candidate.city_slug))
    if venue is None or city is None or candidate.starts_at is None:
        raise ValueError("Candidate is missing venue, city, or start date.")

    duplicate, existing_id = dedupe_candidate(
        CandidateData(
            venue_id=venue.id,
            city_slug=candidate.city_slug,
            source_url=candidate.source_url,
            title=candidate.title,
            starts_at=candidate.starts_at,
            ticket_url=candidate.ticket_url,
        ),
        db,
    )
    if duplicate and existing_id:
        candidate.status = "duplicate"
        candidate.existing_event_id = existing_id
        db.commit()
        existing = db.get(Event, existing_id)
        if existing is not None:
            return existing

    source = ensure_venue_page_source(db)
    artist = find_or_create_artist(db, candidate.artist or candidate.title)
    needs_review = candidate.confidence_score < 0.75
    event = Event(
        city_id=city.id,
        venue_id=venue.id,
        artist_id=artist.id,
        source_id=source.id,
        title=candidate.title,
        slug=event_slug(candidate.title, candidate.starts_at),
        starts_at=candidate.starts_at,
        ticket_url=candidate.ticket_url,
        source_url=candidate.source_url,
        image_url=candidate.image_url,
        price_min=parse_price(candidate.price_text),
        source_attribution=f"Venue page auto finder ({candidate.source_type})",
        confidence_score=candidate.confidence_score,
        status="review" if needs_review else "scheduled",
        needs_review=needs_review,
        normalized_fingerprint=fingerprint_parts(
            city.slug,
            candidate.title,
            venue.name,
            candidate.starts_at,
        ),
        raw_payload={
            "candidate_id": candidate.id,
            "source_type": candidate.source_type,
            "raw_payload": candidate.raw_payload,
        },
    )
    db.add(event)
    db.flush()
    candidate.status = "approved"
    candidate.existing_event_id = event.id
    db.commit()
    db.refresh(event)
    return event


def scrape_run_payload(run: ScrapeRun | None) -> dict[str, Any]:
    if run is None:
        return {
            "status": "never_run",
            "venues_checked": 0,
            "events_found": 0,
            "events_created": 0,
            "events_needing_review": 0,
            "errors": [],
            "warnings": [],
        }
    return {
        "id": run.id,
        "city_slug": run.city_slug,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status,
        "venues_checked": run.venues_checked,
        "events_found": run.events_found,
        "events_created": run.events_created,
        "events_needing_review": run.events_needing_review,
        "errors": split_lines(run.errors),
        "warnings": split_lines(run.warnings),
    }


def candidate_payload(candidate: ExtractedEventCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "venue_id": candidate.venue_id,
        "venue_name": candidate.venue.name if candidate.venue else None,
        "city_slug": candidate.city_slug,
        "source_url": candidate.source_url,
        "source_type": candidate.source_type,
        "raw_title": candidate.raw_title,
        "title": candidate.title,
        "artist": candidate.artist,
        "starts_at": candidate.starts_at.isoformat() if candidate.starts_at else None,
        "price_text": candidate.price_text,
        "ticket_url": candidate.ticket_url,
        "image_url": candidate.image_url,
        "confidence_score": candidate.confidence_score,
        "status": candidate.status,
        "existing_event_id": candidate.existing_event_id,
        "raw_payload": candidate.raw_payload,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
    }


def store_candidate(db: Session, venue: Venue, candidate: CandidateData) -> ExtractedEventCandidate:
    duplicate, existing_event_id = dedupe_candidate(candidate, db)
    status = "duplicate" if duplicate else "needs_review"
    stored = ExtractedEventCandidate(
        venue_id=venue.id,
        city_slug=venue.city.slug,
        source_url=candidate.source_url,
        source_type=candidate.source_type,
        raw_title=candidate.raw_title,
        title=candidate.title,
        artist=candidate.artist,
        starts_at=candidate.starts_at,
        price_text=candidate.price_text,
        ticket_url=candidate.ticket_url,
        image_url=candidate.image_url,
        confidence_score=candidate.confidence_score,
        status=status,
        existing_event_id=existing_event_id,
        raw_payload=candidate.raw_payload,
    )
    db.add(stored)
    db.flush()
    return stored


def parse_rss_or_atom(raw: str, source_url: str) -> list[CandidateData]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    candidates: list[CandidateData] = []
    for item in root.findall(".//item"):
        title = xml_text(item, "title")
        link = xml_text(item, "link")
        date_text = xml_text(item, "pubDate") or xml_text(item, "date")
        starts_at = parse_datetime(date_text)
        candidates.append(
            CandidateData(
                source_url=link or source_url,
                source_type="rss",
                raw_title=title,
                title=title or "",
                starts_at=starts_at,
                ticket_url=link,
                confidence_score=0.55 if starts_at else 0.35,
                raw_payload={"feed_url": source_url, "date_text": date_text},
            )
        )
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = xml_text(entry, "{http://www.w3.org/2005/Atom}title")
        link_node = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_node.attrib.get("href") if link_node is not None else None
        date_text = xml_text(entry, "{http://www.w3.org/2005/Atom}updated") or xml_text(entry, "{http://www.w3.org/2005/Atom}published")
        starts_at = parse_datetime(date_text)
        candidates.append(
            CandidateData(
                source_url=link or source_url,
                source_type="rss",
                raw_title=title,
                title=title or "",
                starts_at=starts_at,
                ticket_url=link,
                confidence_score=0.55 if starts_at else 0.35,
                raw_payload={"feed_url": source_url, "date_text": date_text},
            )
        )
    return candidates


def parse_ical_text(raw: str, source_url: str) -> list[CandidateData]:
    candidates: list[CandidateData] = []
    current: dict[str, str] | None = None
    for line in unfold_ical(raw):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT" and current is not None:
            title = current.get("SUMMARY")
            url = current.get("URL")
            starts_at = parse_ical_datetime(current.get("DTSTART"))
            candidates.append(
                CandidateData(
                    source_url=url or source_url,
                    source_type="ical",
                    raw_title=title,
                    title=title or "",
                    starts_at=starts_at,
                    ticket_url=url,
                    confidence_score=0.6 if starts_at else 0.35,
                    raw_payload={
                        "feed_url": source_url,
                        "uid": current.get("UID"),
                        "location": current.get("LOCATION"),
                    },
                )
            )
            current = None
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";", 1)[0]] = value.strip()
    return candidates


def candidate_from_json_ld(event: dict[str, Any], source_url: str) -> CandidateData:
    offers = first_item(event.get("offers"))
    location = first_item(event.get("location"))
    image = first_item(event.get("image"))
    ticket_url = value_from(offers, "url") if isinstance(offers, dict) else None
    price = value_from(offers, "price") if isinstance(offers, dict) else None
    return CandidateData(
        source_url=str(event.get("@id") or event.get("url") or source_url),
        source_type="structured_data",
        raw_title=str(event.get("name") or ""),
        title=str(event.get("name") or ""),
        starts_at=parse_datetime(event.get("startDate")),
        ends_at=parse_datetime(event.get("endDate")),
        price_text=str(price) if price is not None else None,
        ticket_url=ticket_url,
        image_url=image if isinstance(image, str) else None,
        description=str(event.get("description")) if event.get("description") else None,
        confidence_score=0.75,
        raw_payload={
            "location_name": value_from(location, "name") if isinstance(location, dict) else None,
            "location_address": value_from(location, "address") if isinstance(location, dict) else None,
            "description": event.get("description"),
            "source_url": source_url,
        },
    )


def iter_schema_events(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            found.extend(iter_schema_events(item))
    elif isinstance(payload, dict):
        if is_schema_event(payload):
            found.append(payload)
        for key in ["@graph", "mainEntity", "itemListElement"]:
            if key in payload:
                found.extend(iter_schema_events(payload[key]))
    return found


def is_schema_event(value: dict[str, Any]) -> bool:
    raw_type = value.get("@type")
    types = raw_type if isinstance(raw_type, list) else [raw_type]
    return any(str(item).lower() == "event" for item in types)


def discover_feed_links(html: str, base_url: str) -> list[str]:
    return discover_links(html, base_url, {"application/rss+xml", "application/atom+xml"}, {".rss", ".xml", "feed"})


def discover_ical_links(html: str, base_url: str) -> list[str]:
    return discover_links(html, base_url, {"text/calendar"}, {".ics", "ical", "calendar"})


def discover_links(html: str, base_url: str, rel_types: set[str], href_hints: set[str]) -> list[str]:
    parser = LinkParser(base_url)
    parser.feed(html)
    urls: list[str] = []
    for link in parser.links:
        link_type = (link.get("type") or "").lower()
        href = link.get("href") or ""
        href_lower = href.lower()
        if link_type in rel_types or any(hint in href_lower for hint in href_hints):
            absolute = urllib.parse.urljoin(base_url, href)
            if not is_unsupported_url(absolute):
                urls.append(absolute)
    return list(dict.fromkeys(urls))


def require_candidate(db: Session, candidate_id: int) -> ExtractedEventCandidate:
    candidate = db.get(ExtractedEventCandidate, candidate_id)
    if candidate is None:
        raise ValueError("Candidate not found")
    return candidate


def latest_scrape_status(db: Session, city_slug: str = "glasgow") -> dict[str, Any]:
    latest = db.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.city_slug == city_slug)
        .order_by(ScrapeRun.started_at.desc())
    )
    payload = scrape_run_payload(latest)
    payload["candidates_needing_review"] = db.scalar(
        select(func.count(ExtractedEventCandidate.id)).where(
            ExtractedEventCandidate.city_slug == city_slug,
            ExtractedEventCandidate.status == "needs_review",
        )
    ) or 0
    return payload


def list_candidates(db: Session, city_slug: str = "glasgow", status: str | None = None) -> list[dict[str, Any]]:
    statement = (
        select(ExtractedEventCandidate)
        .where(ExtractedEventCandidate.city_slug == city_slug)
        .options(joinedload(ExtractedEventCandidate.venue))
        .order_by(ExtractedEventCandidate.created_at.desc())
    )
    if status:
        statement = statement.where(ExtractedEventCandidate.status == status)
    return [candidate_payload(candidate) for candidate in db.scalars(statement)]


def update_venue_status(venue: Venue, status: str, note: str) -> None:
    venue.scraper_status = status
    venue.scraper_notes = note
    venue.coverage_status = status if status in {"ok", "broken", "unsupported", "manual_only"} else venue.coverage_status
    venue.last_error = note if status in {"broken", "robots_blocked"} else None


def ensure_venue_page_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == "Official venue page auto finder"))
    if source is not None:
        return source
    source = Source(
        name="Official venue page auto finder",
        slug="official-venue-page-auto-finder",
        kind="venue_page",
        is_enabled=True,
        notes="Safe official venue page extraction into manual review.",
        requires_credentials=False,
        current_mode="review_only",
        automation_allowed="official_pages_only",
    )
    db.add(source)
    db.flush()
    return source


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = parsedate_to_datetime(str(value))
    except Exception:
        try:
            parsed = date_parser.parse(str(value), fuzzy=True)
        except Exception:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_ical_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ["%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"]:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return parse_datetime(value)


def unfold_ical(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith((" ", "\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line.strip())
    return lines


def xml_text(node: ET.Element, tag: str) -> str | None:
    found = node.find(tag)
    return clean_text(found.text) if found is not None and found.text else None


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def candidate_key(candidate: CandidateData) -> tuple[str, str | None, str | None]:
    date_key = candidate.starts_at.isoformat() if candidate.starts_at else None
    return (candidate.title.lower(), date_key, candidate.ticket_url or candidate.source_url)


def parse_price(value: str | None) -> Decimal | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d{1,2})?", value)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def value_from(payload: dict[str, Any] | None, key: str) -> str | None:
    if not payload:
        return None
    value = payload.get(key)
    if isinstance(value, dict):
        return value.get("name") or value.get("streetAddress")
    if isinstance(value, list):
        first = first_item(value)
        return str(first) if first is not None else None
    return str(value) if value is not None else None


def first_item(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def is_unsupported_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(part in host for part in UNSUPPORTED_HOST_PARTS)


def looks_like_feed(url: str) -> bool:
    lowered = url.lower()
    return lowered.endswith((".rss", ".xml")) or "feed" in lowered


def looks_like_ical(url: str) -> bool:
    lowered = url.lower()
    return lowered.endswith(".ics") or "ical" in lowered


def split_lines(value: str | None) -> list[str]:
    return [line for line in (value or "").splitlines() if line.strip()]


class JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self._in_json_ld = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "script" and attr_map.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_json_ld:
            self.scripts.append("".join(self._buffer).strip())
            self._in_json_ld = False


class LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in {"link", "a"}:
            return
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if attr_map.get("href"):
            self.links.append(attr_map)


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None" = None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node] = []
        self.text_parts: list[str] = []

    @property
    def text(self) -> str:
        return clean_text(" ".join([*self.text_parts, *(child.text for child in self.children)]))


class HtmlTreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = Node("document", {})
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag.lower(), {name.lower(): value or "" for name, value in attrs}, self.current)
        self.current.children.append(node)
        self.current = node

    def handle_endtag(self, tag: str) -> None:
        if self.current.parent is not None:
            self.current = self.current.parent

    def handle_data(self, data: str) -> None:
        self.current.text_parts.append(data)


def find_all(root: Node, selector: str) -> list[Node]:
    if not selector:
        return []
    parts = selector.strip().split()
    current = [root]
    for part in parts:
        next_nodes: list[Node] = []
        for node in current:
            next_nodes.extend(descendants_matching(node, part))
        current = next_nodes
    return current


def descendants_matching(root: Node, selector: str) -> list[Node]:
    matches: list[Node] = []
    for child in root.children:
        if matches_simple_selector(child, selector):
            matches.append(child)
        matches.extend(descendants_matching(child, selector))
    return matches


def matches_simple_selector(node: Node, selector: str) -> bool:
    selector = selector.strip()
    if selector.startswith("."):
        classes = set((node.attrs.get("class") or "").split())
        return selector[1:] in classes
    if selector.startswith("#"):
        return node.attrs.get("id") == selector[1:]
    return node.tag == selector.lower()


def text_for_selector(root: Node, selector: Any) -> str | None:
    if not selector:
        return None
    nodes = find_all(root, str(selector))
    return nodes[0].text if nodes else None


def url_for_selector(root: Node, selector: Any, base_url: str | None, attr: str = "href") -> str | None:
    if not selector:
        return None
    nodes = find_all(root, str(selector))
    if not nodes:
        return None
    value = nodes[0].attrs.get(attr)
    if not value:
        return None
    return urllib.parse.urljoin(base_url or "", value)
