from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import robotparser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.city import City
from app.models.event import Event
from app.models.venue import Venue
from app.models.venue_check_log import VenueCheckLog
from app.models.venue_coverage import VenueCoverage

SEED_DIR = Path(__file__).resolve().parents[2] / "seeds"
USER_AGENT = "GiggedGlasgowVenueCoverage/0.1 (+manual editorial review)"


DISCOVERY_SOURCES = [
    {
        "name": "Visit Glasgow",
        "url": "https://peoplemakeglasgow.com/",
        "mode": "directory_review",
        "notes": "Use public directory/event pages only when permitted by terms and robots.txt.",
    },
    {
        "name": "What's On Glasgow",
        "url": "https://www.whatsonglasgow.co.uk/",
        "mode": "directory_review",
        "notes": "Treat as a venue discovery lead source; do not copy protected listings wholesale.",
    },
    {
        "name": "Skiddle",
        "url": "https://www.skiddle.com/",
        "mode": "partner_or_manual_review",
        "notes": "Prefer official APIs/partner exports where available.",
    },
    {
        "name": "Gigs in Scotland",
        "url": "https://www.gigsinscotland.com/",
        "mode": "directory_review",
        "notes": "Use as attribution-aware cross-check for promoted gigs.",
    },
    {
        "name": "Gig Guide",
        "url": "https://www.gig-guide.co.uk/",
        "mode": "directory_review",
        "notes": "Use for venue discovery leads and manual audit.",
    },
    {
        "name": "Eventbrite",
        "url": "https://www.eventbrite.co.uk/",
        "mode": "official_api_preferred",
        "notes": "Use official API or organiser-provided public pages where permitted.",
    },
    {
        "name": "Ticketmaster",
        "url": "https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/",
        "mode": "official_api",
        "notes": "Official Discovery API source already supported by the ingestion engine.",
    },
    {
        "name": "Venue websites",
        "url": None,
        "mode": "robots_terms_checked",
        "notes": "Official venue pages are preferred when robots.txt and terms allow access.",
    },
    {
        "name": "Promoter sites",
        "url": None,
        "mode": "robots_terms_checked",
        "notes": "Use promoter pages as leads and keep source attribution internal.",
    },
    {
        "name": "Manual CSV",
        "url": None,
        "mode": "manual_import",
        "notes": "Fallback for venues and events supplied by editors, promoters, or venue teams.",
    },
]


@dataclass(slots=True)
class VenueCheckResult:
    venue_id: int
    venue_name: str
    status: str
    source_name: str
    source_url: str | None
    coverage_type: str
    coverage_status: str
    confidence_score: float
    events_found: int
    message: str
    structure_changed: bool


def seed_glasgow_venue_coverage(db: Session) -> int:
    city = db.scalar(select(City).where(City.slug == "glasgow"))
    if city is None:
        raise ValueError("Glasgow must be seeded before venue coverage can be seeded.")

    records = json.loads((SEED_DIR / "glasgow_venue_coverage.json").read_text(encoding="utf-8"))
    upserted = 0
    for item in records:
        slug = item.get("slug") or slugify(item["name"])
        venue = db.scalar(select(Venue).where(Venue.city_id == city.id, Venue.slug == slug))
        if venue is None:
            venue = Venue(city_id=city.id, slug=slug, name=item["name"], is_whitelisted=True)
            db.add(venue)
            db.flush()
        venue.name = item["name"]
        venue.address = item.get("address")
        venue.postcode = item.get("postcode")
        venue.capacity = item.get("capacity")
        venue.website_url = item.get("website_url")
        venue.event_listings_url = item.get("event_listings_url")
        venue.ticketing_url = item.get("ticketing_url")
        venue.instagram_handle = item.get("instagram_handle")
        venue.source_discovered_from = item.get("source_discovered_from")
        venue.coverage_status = item.get("coverage_status") or venue.coverage_status or "manual_only"
        venue.status = item.get("status") or venue.status or "active"
        venue.notes = item.get("notes")
        venue.is_whitelisted = True
        upsert_venue_coverage(
            db,
            venue=venue,
            source_name=item.get("source_name") or "Official venue page",
            source_url=item.get("event_listings_url") or item.get("website_url"),
            coverage_type=item.get("coverage_type") or infer_seed_coverage_type(item),
            status=item.get("coverage_source_status") or "needs_review",
            error_message=None,
            confidence_score=0.5,
            preserve_checked_state=True,
        )
        upserted += 1
    db.commit()
    return upserted


def venue_coverage_payload(db: Session, city_slug: str = "glasgow") -> dict[str, Any]:
    city = require_city(db, city_slug)
    venues = list(
        db.scalars(
            select(Venue)
            .where(Venue.city_id == city.id)
            .options(
                joinedload(Venue.check_logs),
                joinedload(Venue.coverage_sources),
                joinedload(Venue.events),
            )
            .order_by(Venue.name.asc())
        )
        .unique()
    )
    summary = build_coverage_summary(db, venues)
    return {
        "city": city.name,
        "city_slug": city.slug,
        "summary": summary,
        "pre_publish_report": build_pre_publish_report(summary, venues),
        "discovery_sources": DISCOVERY_SOURCES,
        "venues": [venue_payload(venue) for venue in venues],
    }


def run_all_venue_checks(db: Session, city_slug: str = "glasgow", live_http: bool = False) -> dict[str, Any]:
    city = require_city(db, city_slug)
    venues = list(db.scalars(select(Venue).where(Venue.city_id == city.id).order_by(Venue.name.asc())))
    results = [check_venue_now(db, venue.id, live_http=live_http) for venue in venues]
    payload = venue_coverage_payload(db, city_slug)
    payload["check_results"] = [asdict(result) for result in results]
    return payload


def check_venue_now(db: Session, venue_id: int, live_http: bool = True) -> VenueCheckResult:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise ValueError("Venue not found")

    now = datetime.utcnow()
    supported_sources = detect_supported_sources(venue)
    candidate_url = venue.event_listings_url or guess_events_url(venue.website_url)
    source_name = "Official venue page" if candidate_url else "Manual editorial fallback"
    coverage_type = "website" if candidate_url else "manual"
    source_status = "needs_review"
    error_message = None
    future_event_count = db.scalar(
        select(func.count(Event.id)).where(Event.venue_id == venue.id, Event.starts_at >= now)
    ) or 0

    robots_checked = False
    structure_changed = False
    confidence = 0.35
    message = "Venue is stored for manual coverage; no supported event URL is available yet."
    coverage_status = "manual_only"
    status = venue.status if venue.status != "closed" else "closed"
    raw_payload: dict[str, Any] = {
        "candidate_url": candidate_url,
        "supported_sources": supported_sources,
        "live_http": live_http,
        "ethical_limits": [
            "No login, paywall, CAPTCHA, robots.txt bypass, or anti-bot circumvention.",
            "Official APIs, RSS, structured data, venue pages, and manual review are preferred.",
        ],
    }

    if candidate_url and not live_http:
        coverage_status = "manual_only"
        status = "active"
        source_status = "needs_review"
        confidence = 0.55
        message = "Batch preflight confirmed venue source metadata; run Check now for a live robots-aware page check."
    elif candidate_url:
        allowed, robots_message = robots_allows(candidate_url)
        robots_checked = True
        raw_payload["robots_message"] = robots_message
        if allowed:
            page_status = fetch_public_page_status(candidate_url)
            raw_payload["page_status"] = page_status
            if page_status["ok"]:
                coverage_status = "automated"
                status = "active"
                source_status = "working"
                confidence = 0.75
                if page_status["has_event_signals"]:
                    confidence = 0.9
                    message = "Official events page is reachable and contains event-like signals."
                else:
                    structure_changed = True
                    source_status = "needs_review"
                    confidence = 0.62
                    message = "Official page is reachable, but expected event signals were not found."
            else:
                coverage_status = "broken"
                source_status = "broken"
                structure_changed = bool(page_status.get("structure_changed"))
                confidence = 0.25
                message = page_status["message"]
                error_message = message
        else:
            coverage_type = "unsupported"
            coverage_status = "unsupported"
            source_status = "needs_review"
            confidence = 0.2
            message = robots_message
            error_message = robots_message

    if future_event_count:
        venue.last_event_found_at = latest_event_datetime(db, venue.id)
        confidence = max(confidence, 0.82)
        if coverage_status in {"manual_only", "unsupported"} and supported_sources and source_status == "working":
            coverage_status = "automated"
        message = f"{future_event_count} upcoming events already linked to this venue."

    if venue.status == "closed":
        source_status = "inactive"
        status = "closed"

    venue.last_checked_at = now
    venue.coverage_status = coverage_status
    venue.status = status
    if candidate_url and not venue.event_listings_url:
        venue.event_listings_url = candidate_url
    if message:
        venue.notes = merge_note(venue.notes, message)

    coverage = upsert_venue_coverage(
        db,
        venue=venue,
        source_name=source_name,
        source_url=candidate_url,
        coverage_type=coverage_type,
        status=source_status,
        last_checked_at=now,
        last_successful_event_found_at=venue.last_event_found_at if future_event_count else None,
        error_message=error_message,
        confidence_score=confidence,
    )

    log = VenueCheckLog(
        venue_id=venue.id,
        checked_at=now,
        status=status,
        coverage_status=coverage_status,
        confidence_score=confidence,
        events_found=future_event_count,
        official_events_url=candidate_url,
        supported_sources=", ".join(supported_sources) if supported_sources else None,
        robots_checked=robots_checked,
        structure_changed=structure_changed,
        message=message,
        raw_payload=raw_payload,
    )
    db.add(log)
    db.commit()
    db.refresh(venue)
    return VenueCheckResult(
        venue_id=venue.id,
        venue_name=venue.name,
        status=coverage.status,
        source_name=coverage.source_name,
        source_url=coverage.source_url,
        coverage_type=coverage.coverage_type,
        coverage_status=coverage_status,
        confidence_score=confidence,
        events_found=future_event_count,
        message=message,
        structure_changed=structure_changed,
    )


def build_coverage_summary(db: Session, venues: list[Venue]) -> dict[str, Any]:
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(days=30)
    total = len(venues)
    upcoming_counts = upcoming_event_counts(db, venues)
    automated = count_where(venues, has_working_automated_source)
    manual_only = count_where(venues, is_manual_only)
    needs_review = count_where(venues, lambda venue: any(source.status == "needs_review" for source in venue.coverage_sources))
    broken = sum(1 for venue in venues for source in venue.coverage_sources if source.status == "broken")
    unsupported = count_where(venues, lambda venue: any(source.coverage_type == "unsupported" for source in venue.coverage_sources))
    duplicate = count_where(venues, lambda venue: venue.status == "duplicate")
    monitored = count_where(
        venues,
        lambda venue: venue.status in {"active", "needs_review"}
        and any(source.status in {"working", "needs_review", "broken"} for source in venue.coverage_sources),
    )
    successful_event_pulls = count_where(
        venues,
        lambda venue: any(source.last_successful_event_found_at for source in venue.coverage_sources),
    )
    no_events_found = count_where(venues, lambda venue: upcoming_counts.get(venue.id, 0) == 0)
    not_checked_30_days = count_where(
        venues,
        lambda venue: source_stale(venue, stale_cutoff),
    )
    possible_duplicate_groups = possible_duplicate_count(venues)
    score = calculate_score(total, automated, manual_only, needs_review, broken, unsupported, duplicate, not_checked_30_days)
    sources_checked = sum(
        1
        for venue in venues
        for source in venue.coverage_sources
        if source.last_checked_at is not None
    )
    sources_working = sum(
        1
        for venue in venues
        for source in venue.coverage_sources
        if source.status == "working"
    )
    sources_failed = broken
    explanation = (
        f"{total} venues tracked, {automated} automated, {manual_only} manual-only, "
        f"{needs_review} need review."
    )
    return {
        "total_venues": total,
        "automated_venues": automated,
        "manual_only_venues": manual_only,
        "broken_venue_sources": broken,
        "venues_not_checked_in_30_days": not_checked_30_days,
        "venues_with_no_upcoming_events": no_events_found,
        "coverage_percentage": score,
        "sources_checked": sources_checked,
        "sources_working": sources_working,
        "sources_failed": sources_failed,
        "total_venues_discovered": total,
        "venues_currently_monitored": monitored,
        "venues_with_successful_event_pulls": successful_event_pulls,
        "venues_with_no_events_found": no_events_found,
        "venues_needing_manual_review": needs_review,
        "broken_source_links": broken,
        "possible_duplicates": duplicate + possible_duplicate_groups,
        "venues_not_checked_30_days": not_checked_30_days,
        "automated": automated,
        "manual_only": manual_only,
        "unsupported": unsupported,
        "coverage_score": score,
        "explanation": explanation,
        "missing": build_missing_list(total, manual_only, needs_review, broken, unsupported, not_checked_30_days, no_events_found),
        "venues_may_be_missing_events": venues_missing_events(venues, upcoming_counts),
    }


def venue_payload(venue: Venue) -> dict[str, Any]:
    latest_log = max(venue.check_logs, key=lambda log: log.checked_at, default=None)
    return {
        "id": venue.id,
        "venue_name": venue.name,
        "name": venue.name,
        "slug": venue.slug,
        "address": venue.address,
        "postcode": venue.postcode,
        "website": venue.website_url,
        "website_url": venue.website_url,
        "event_listings_url": venue.event_listings_url,
        "ticketing_url": venue.ticketing_url,
        "instagram_handle": venue.instagram_handle,
        "source_discovered_from": venue.source_discovered_from,
        "last_checked_at": venue.last_checked_at.isoformat() if venue.last_checked_at else None,
        "last_event_found_at": venue.last_event_found_at.isoformat() if venue.last_event_found_at else None,
        "status": venue.status,
        "coverage_status": venue.coverage_status,
        "notes": venue.notes,
        "upcoming_events": upcoming_event_count_for_venue(venue),
        "coverage_sources": [coverage_source_payload(source) for source in venue.coverage_sources],
        "latest_check": {
            "checked_at": latest_log.checked_at.isoformat(),
            "confidence_score": latest_log.confidence_score,
            "events_found": latest_log.events_found,
            "message": latest_log.message,
            "structure_changed": latest_log.structure_changed,
        }
        if latest_log
        else None,
    }


def coverage_source_payload(source: VenueCoverage) -> dict[str, Any]:
    return {
        "id": source.id,
        "source_name": source.source_name,
        "source_url": source.source_url,
        "coverage_type": source.coverage_type,
        "status": source.status,
        "last_checked_at": source.last_checked_at.isoformat() if source.last_checked_at else None,
        "last_successful_event_found_at": (
            source.last_successful_event_found_at.isoformat()
            if source.last_successful_event_found_at
            else None
        ),
        "error_message": source.error_message,
        "confidence_score": source.confidence_score,
    }


def require_city(db: Session, city_slug: str) -> City:
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise ValueError(f"City '{city_slug}' has not been seeded.")
    return city


def detect_supported_sources(venue: Venue) -> list[str]:
    values = " ".join(
        value.lower()
        for value in [venue.website_url, venue.event_listings_url, venue.ticketing_url]
        if value
    )
    supported = []
    if "ticketmaster" in values:
        supported.append("Ticketmaster Discovery API")
    if "eventbrite" in values:
        supported.append("Eventbrite official/public export review")
    if "skiddle" in values:
        supported.append("Skiddle partner/manual review")
    if "gigsinscotland" in values:
        supported.append("Gigs in Scotland directory review")
    if venue.event_listings_url or venue.website_url:
        supported.append("Official venue page")
    return supported


def upsert_venue_coverage(
    db: Session,
    venue: Venue,
    source_name: str,
    source_url: str | None,
    coverage_type: str,
    status: str,
    last_checked_at: datetime | None = None,
    last_successful_event_found_at: datetime | None = None,
    error_message: str | None = None,
    confidence_score: float = 0.5,
    preserve_checked_state: bool = False,
) -> VenueCoverage:
    coverage = db.scalar(
        select(VenueCoverage).where(
            VenueCoverage.venue_id == venue.id,
            VenueCoverage.source_name == source_name,
        )
    )
    if coverage is None:
        coverage = VenueCoverage(venue_id=venue.id, source_name=source_name)
        db.add(coverage)
        db.flush()

    coverage.source_url = source_url
    coverage.coverage_type = coverage_type
    if not preserve_checked_state or coverage.last_checked_at is None:
        coverage.status = status
        coverage.last_checked_at = last_checked_at
        coverage.last_successful_event_found_at = last_successful_event_found_at
        coverage.error_message = error_message
        coverage.confidence_score = confidence_score
    return coverage


def infer_seed_coverage_type(item: dict[str, Any]) -> str:
    values = " ".join(
        str(value).lower()
        for value in [item.get("event_listings_url"), item.get("ticketing_url"), item.get("website_url")]
        if value
    )
    if "ticketmaster" in values:
        return "api"
    if item.get("event_listings_url") or item.get("website_url"):
        return "website"
    return "manual"


def has_working_automated_source(venue: Venue) -> bool:
    return any(
        source.coverage_type in {"api", "website"} and source.status == "working"
        for source in venue.coverage_sources
    )


def is_manual_only(venue: Venue) -> bool:
    if not venue.coverage_sources:
        return True
    return not any(
        source.coverage_type in {"api", "website"} and source.status == "working"
        for source in venue.coverage_sources
    )


def source_stale(venue: Venue, stale_cutoff: datetime) -> bool:
    if not venue.coverage_sources:
        return True
    return all(
        source.last_checked_at is None or source.last_checked_at < stale_cutoff
        for source in venue.coverage_sources
    )


def upcoming_event_counts(db: Session, venues: list[Venue]) -> dict[int, int]:
    if not venues:
        return {}
    venue_ids = [venue.id for venue in venues]
    rows = db.execute(
        select(Event.venue_id, func.count(Event.id))
        .where(Event.venue_id.in_(venue_ids), Event.starts_at >= datetime.utcnow())
        .group_by(Event.venue_id)
    ).all()
    return {venue_id: count for venue_id, count in rows}


def upcoming_event_count_for_venue(venue: Venue) -> int:
    now = datetime.utcnow()
    return sum(1 for event in venue.events if event.starts_at >= now and event.status != "rejected")


def venues_missing_events(venues: list[Venue], upcoming_counts: dict[int, int]) -> list[dict[str, Any]]:
    missing = []
    for venue in venues:
        if upcoming_counts.get(venue.id, 0) > 0:
            continue
        missing.append(
            {
                "venue_id": venue.id,
                "venue_name": venue.name,
                "reason": "No upcoming events are currently linked to this venue.",
                "coverage_sources": [
                    coverage_source_payload(source) for source in venue.coverage_sources
                ],
            }
        )
    return missing


def build_pre_publish_report(summary: dict[str, Any], venues: list[Venue]) -> dict[str, Any]:
    missing_events = summary.get("venues_may_be_missing_events", [])
    sources_failed = summary.get("sources_failed", 0)
    stale = summary.get("venues_not_checked_in_30_days", 0)
    coverage_percentage = summary.get("coverage_percentage", 0)
    safe_to_publish = (
        sources_failed == 0
        and stale == 0
        and coverage_percentage >= 70
        and len(missing_events) <= max(2, len(venues) // 4)
    )
    return {
        "venues_checked": summary.get("sources_checked", 0),
        "sources_worked": summary.get("sources_working", 0),
        "sources_failed": sources_failed,
        "venues_may_be_missing_events": missing_events,
        "safe_to_publish": safe_to_publish,
        "publish_warning": None
        if safe_to_publish
        else "Coverage needs editorial review before publishing the weekly roundup.",
    }


def guess_events_url(website_url: str | None) -> str | None:
    if not website_url:
        return None
    return urljoin(website_url.rstrip("/") + "/", "events")


def robots_allows(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False, "Invalid event URL; manual review required."
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=3) as response:
            robots_body = response.read(120_000).decode("utf-8", errors="ignore").splitlines()
        parser.parse(robots_body)
    except (OSError, URLError, socket.timeout):
        return True, "robots.txt could not be read; proceeding only with a lightweight public page check."
    if not parser.can_fetch(USER_AGENT, url):
        return False, "robots.txt disallows automated checks for this event URL."
    return True, "robots.txt permits this lightweight public page check."


def fetch_public_page_status(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=5) as response:
            status_code = getattr(response, "status", 200)
            content_type = response.headers.get("content-type", "")
            body = response.read(120_000).decode("utf-8", errors="ignore").lower()
    except HTTPError as exc:
        return {
            "ok": False,
            "status_code": exc.code,
            "structure_changed": exc.code in {404, 410},
            "has_event_signals": False,
            "message": f"Event page returned HTTP {exc.code}; source link needs review.",
        }
    except (OSError, URLError, socket.timeout) as exc:
        return {
            "ok": False,
            "status_code": None,
            "structure_changed": False,
            "has_event_signals": False,
            "message": f"Could not reach event page: {exc.__class__.__name__}.",
        }

    signals = ["event", "gig", "concert", "tickets", "json-ld", "schema.org/event"]
    return {
        "ok": 200 <= int(status_code) < 400,
        "status_code": status_code,
        "content_type": content_type,
        "structure_changed": False,
        "has_event_signals": any(signal in body for signal in signals),
        "message": "Public page check completed.",
    }


def latest_event_datetime(db: Session, venue_id: int) -> datetime | None:
    return db.scalar(
        select(Event.starts_at)
        .where(Event.venue_id == venue_id, Event.starts_at >= datetime.utcnow())
        .order_by(Event.starts_at.desc())
        .limit(1)
    )


def merge_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing}\nLatest check: {note}"


def count_where(venues: list[Venue], predicate) -> int:
    return sum(1 for venue in venues if predicate(venue))


def possible_duplicate_count(venues: list[Venue]) -> int:
    seen: dict[str, int] = {}
    for venue in venues:
        key = slugify(venue.name)
        seen[key] = seen.get(key, 0) + 1
    return sum(count - 1 for count in seen.values() if count > 1)


def calculate_score(
    total: int,
    automated: int,
    manual_only: int,
    needs_review: int,
    broken: int,
    unsupported: int,
    duplicate: int,
    stale: int,
) -> int:
    if total == 0:
        return 0
    raw = 100
    raw -= int((manual_only / total) * 20)
    raw -= int((needs_review / total) * 20)
    raw -= int((broken / total) * 25)
    raw -= int((unsupported / total) * 15)
    raw -= int((duplicate / total) * 10)
    raw -= int((stale / total) * 10)
    raw += int((automated / total) * 15)
    return max(0, min(100, raw))


def build_missing_list(
    total: int,
    manual_only: int,
    needs_review: int,
    broken: int,
    unsupported: int,
    stale: int,
    no_events_found: int,
) -> list[str]:
    if total == 0:
        return ["No venues have been discovered yet."]
    missing = []
    if manual_only:
        missing.append(f"{manual_only} venues still need automated source coverage.")
    if needs_review:
        missing.append(f"{needs_review} venues need editorial review.")
    if broken:
        missing.append(f"{broken} venue source links are broken.")
    if unsupported:
        missing.append(f"{unsupported} venues are blocked or unsupported for automated checks.")
    if stale:
        missing.append(f"{stale} venues have not been checked in the last 30 days.")
    if no_events_found:
        missing.append(f"{no_events_found} venues currently have no upcoming events linked.")
    return missing or ["Coverage is healthy for the current venue set."]
