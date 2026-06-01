from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from slugify import slugify
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.artist import Artist
from app.models.city import City
from app.models.event import Event
from app.models.ingestion_log import IngestionLog
from app.models.ingestion_run import IngestionRun
from app.models.raw_event import RawEvent
from app.models.source import Source
from app.models.venue import Venue
from app.services.normalization import (
    clean_name,
    confidence_score,
    ensure_aware,
    event_fingerprint,
    event_slug,
    needs_review,
)
from app.services.app_settings import get_raw_setting
from app.services.seed import seed_glasgow
from app.services.source_health import adapter_metadata, record_source_ingest
from app.sources.base import EventSourceAdapter, NormalizedSourceEvent
from app.sources.registry import get_default_adapters


@dataclass(slots=True)
class IngestionReport:
    city: str
    fetched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failures: int = 0
    warnings: list[str] = field(default_factory=list)
    source_logs: list[dict] = field(default_factory=list)


UpsertOutcome = Literal["created", "updated", "skipped", "duplicate"]


def ingest_city(
    db: Session,
    city_slug: str,
    adapters: list[EventSourceAdapter] | None = None,
) -> IngestionReport:
    config = get_city_config(city_slug)
    if city_slug == "glasgow":
        seed_glasgow(db)

    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise ValueError(f"City '{city_slug}' has not been seeded.")

    start = datetime.now(timezone.utc)
    try:
        date_range_days = int(get_raw_setting(db, "date_range_days") or 30)
    except ValueError:
        date_range_days = 30
    end = start + timedelta(days=max(1, min(date_range_days, 180)))
    report = IngestionReport(city=city_slug)

    for adapter in adapters or default_adapters_for_db(db):
        source = ensure_source(db, adapter.name, adapter.kind)
        apply_adapter_metadata(source, adapter)
        configured = adapter_configured(db, adapter)
        log = IngestionLog(
            city_id=city.id,
            source_id=source.id,
            source_name=adapter.name,
            city_slug=city_slug,
            events_found=0,
            events_created=0,
            events_updated=0,
            duplicates_skipped=0,
            failures=0,
            warnings=[],
            started_at=datetime.utcnow(),
        )
        db.add(log)
        run = IngestionRun(
            city_id=city.id,
            source_id=source.id,
            source_name=adapter.name,
            city_slug=city_slug,
            status="running",
            warnings=[],
            started_at=log.started_at,
        )
        db.add(run)
        db.flush()
        if not source.is_enabled:
            warning = f"{adapter.name} source is disabled; ingestion skipped."
            log.warnings = [warning]
            log.finished_at = datetime.utcnow()
            finish_ingestion_run(run, status="skipped", warnings=[warning])
            report.warnings.append(warning)
            report.source_logs.append(ingestion_log_payload(log))
            record_source_ingest(db, source, None, configured, 0, [warning], 0)
            continue
        if source.current_mode == "placeholder":
            warning = f"{adapter.name} is a placeholder source; ingestion skipped."
            log.warnings = [warning]
            log.finished_at = datetime.utcnow()
            finish_ingestion_run(run, status="skipped", warnings=[warning])
            report.warnings.append(warning)
            report.source_logs.append(ingestion_log_payload(log))
            record_source_ingest(db, source, None, configured, 0, [warning], 0)
            continue
        if source.requires_credentials and not configured:
            warning = f"{adapter.name} source is not configured; ingestion skipped."
            log.warnings = [warning]
            log.finished_at = datetime.utcnow()
            finish_ingestion_run(run, status="skipped", warnings=[warning])
            report.warnings.append(warning)
            report.source_logs.append(ingestion_log_payload(log))
            record_source_ingest(db, source, None, configured, 0, [warning], 0)
            continue

        try:
            result = adapter.fetch(config, start, end)
        except Exception as exc:  # pragma: no cover - defensive guard around external adapters
            result = None
            log.failures = 1
            log.warnings = [f"{adapter.name} failed: {exc}"]
            report.failures += 1
            report.warnings.extend(log.warnings)
            log.finished_at = datetime.utcnow()
            finish_ingestion_run(run, status="failed", failures=1, warnings=log.warnings)
            record_source_ingest(db, source, result, configured, 1, log.warnings, 0)
            continue

        seen_source_ids: set[str] = set()
        seen_fingerprints: set[str] = set()
        report.warnings.extend(result.warnings)
        report.warnings.extend(result.failures)
        report.fetched += len(result.events)
        report.failures += len(result.failures)
        log.events_found = len(result.events)
        log.failures = len(result.failures)
        log.warnings = result.warnings + result.failures
        run.events_fetched = len(result.events)
        run.failures = len(result.failures)
        run.warnings = log.warnings

        for source_event in result.events:
            source_event.starts_at = ensure_aware(source_event.starts_at)
            raw_event = store_raw_event(db, city, source, run, log, source_event)
            run.raw_events_stored += 1
            fingerprint = event_fingerprint(city.slug, source_event)
            if source_event.source_event_id and source_event.source_event_id in seen_source_ids:
                mark_raw_duplicate(raw_event, "Duplicate source_event_id inside the same ingestion result.")
                report.skipped += 1
                log.duplicates_skipped += 1
                run.duplicates_marked += 1
                continue
            if fingerprint in seen_fingerprints:
                mark_raw_duplicate(raw_event, "Duplicate fingerprint inside the same ingestion result.")
                report.skipped += 1
                log.duplicates_skipped += 1
                run.duplicates_marked += 1
                continue
            if source_event.source_event_id:
                seen_source_ids.add(source_event.source_event_id)
            seen_fingerprints.add(fingerprint)

            outcome = upsert_event(db, city, config.venue_whitelist, source, source_event, raw_event)
            if outcome == "skipped":
                report.skipped += 1
                log.duplicates_skipped += 1
            elif outcome == "duplicate":
                report.skipped += 1
                log.duplicates_skipped += 1
                run.duplicates_marked += 1
            elif outcome == "created":
                report.created += 1
                log.events_created += 1
                run.events_created += 1
            else:
                report.updated += 1
                log.events_updated += 1
                run.events_updated += 1

        log.finished_at = datetime.utcnow()
        finish_ingestion_run(run, status="completed" if not result.failures else "completed_with_warnings")
        report.source_logs.append(ingestion_log_payload(log))
        record_source_ingest(
            db,
            source,
            result,
            configured,
            len(result.failures),
            log.warnings,
            len(result.events),
        )

    db.commit()
    return report


def upsert_event(
    db: Session,
    city: City,
    venue_whitelist: list[str],
    source: Source,
    source_event: NormalizedSourceEvent,
    raw_event: RawEvent | None = None,
) -> UpsertOutcome:
    source_event.starts_at = ensure_aware(source_event.starts_at)
    fingerprint = event_fingerprint(city.slug, source_event)
    event = None
    if source_event.source_event_id:
        event = db.scalar(
            select(Event).where(
                Event.city_id == city.id,
                Event.source_id == source.id,
                Event.source_event_id == source_event.source_event_id,
            )
        )

    fingerprint_match = db.scalar(
        select(Event).where(Event.city_id == city.id, Event.normalized_fingerprint == fingerprint)
    )
    if event is not None and fingerprint_match is not None and event.id != fingerprint_match.id:
        mark_event_duplicate_review(
            fingerprint_match,
            f"Conflicting source id {source_event.source_event_id or 'unknown'} matched this fingerprint.",
        )
        mark_event_duplicate_review(event, f"Conflicts with event {fingerprint_match.id}.")
        if raw_event:
            raw_event.status = "duplicate_review"
            raw_event.duplicate_of_event_id = fingerprint_match.id
            raw_event.review_reason = "Conflicting source id matched an existing normalised fingerprint."
        return "duplicate"
    if event is None:
        if fingerprint_match is not None:
            mark_event_duplicate_review(
                fingerprint_match,
                f"{source.name} returned a likely duplicate; raw event kept for review.",
            )
            if raw_event:
                raw_event.status = "duplicate_review"
                raw_event.duplicate_of_event_id = fingerprint_match.id
                raw_event.review_reason = "Likely duplicate by artist/title, venue, and date."
            return "duplicate"

    venue = find_or_create_venue(db, city, venue_whitelist, source_event.venue_name)
    if source_event.venue_address and not venue.address:
        venue.address = source_event.venue_address
    if source_event.venue_postcode and not venue.postcode:
        venue.postcode = source_event.venue_postcode
    if source_event.latitude is not None and venue.latitude is None:
        venue.latitude = source_event.latitude
    if source_event.longitude is not None and venue.longitude is None:
        venue.longitude = source_event.longitude
    artist = find_or_create_artist(db, source_event.artist_name or source_event.title)
    score = confidence_score(source_event, venue.is_whitelisted)
    likely_duplicate = None if event is not None else find_likely_duplicate(db, city, venue, artist, source_event)

    created = event is None
    if event is None:
        event = Event(
            city_id=city.id,
            normalized_fingerprint=fingerprint,
            slug=event_slug(source_event.title, source_event.starts_at),
            title=source_event.title,
            starts_at=source_event.starts_at,
        )
        db.add(event)
        db.flush()

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
    event.venue_address = source_event.venue_address
    event.venue_postcode = source_event.venue_postcode
    event.latitude = source_event.latitude
    event.longitude = source_event.longitude
    event.price_min = source_event.price_min
    event.price_max = source_event.price_max
    event.currency = source_event.currency
    event.genre = source_event.genre
    event.status = source_event.status
    event.confidence_score = max(score, event.confidence_score or 0)
    event.source_event_id = source_event.source_event_id
    event.source_attribution = source_event.source_attribution
    event.needs_review = needs_review(event.confidence_score, venue.is_whitelisted)
    event.raw_payload = source_event.raw_payload
    if raw_event:
        raw_event.event_id = event.id
        raw_event.status = "normalised"
    if likely_duplicate is not None:
        mark_event_duplicate_review(
            event,
            f"Likely duplicate of event {likely_duplicate.id}: same/similar artist-title, venue, date, and time.",
            duplicate_of_event_id=likely_duplicate.id,
        )
        if raw_event:
            raw_event.status = "duplicate_review"
            raw_event.duplicate_of_event_id = likely_duplicate.id
            raw_event.review_reason = event.duplicate_reason
        return "duplicate"
    return "created" if created else "updated"


def store_raw_event(
    db: Session,
    city: City,
    source: Source,
    run: IngestionRun,
    log: IngestionLog,
    source_event: NormalizedSourceEvent,
) -> RawEvent:
    raw_event = RawEvent(
        ingestion_run_id=run.id,
        ingestion_log_id=log.id,
        city_id=city.id,
        source_id=source.id,
        city_slug=city.slug,
        source_name=source.name,
        source_event_id=source_event.source_event_id,
        title=source_event.title,
        venue_name=source_event.venue_name,
        starts_at=source_event.starts_at,
        status="fetched",
        raw_payload=json_safe(source_event.raw_payload or {}),
        normalized_payload=json_safe(asdict(source_event)),
    )
    db.add(raw_event)
    db.flush()
    return raw_event


def mark_raw_duplicate(raw_event: RawEvent, reason: str) -> None:
    raw_event.status = "duplicate_review"
    raw_event.review_reason = reason


def mark_event_duplicate_review(
    event: Event,
    reason: str,
    duplicate_of_event_id: int | None = None,
) -> None:
    event.needs_review = True
    if event.status not in {"rejected", "published"}:
        event.status = "duplicate_review"
    event.duplicate_reason = reason
    if duplicate_of_event_id is not None:
        event.duplicate_of_event_id = duplicate_of_event_id


def find_likely_duplicate(
    db: Session,
    city: City,
    venue: Venue,
    artist: Artist,
    source_event: NormalizedSourceEvent,
) -> Event | None:
    starts_at = ensure_aware(source_event.starts_at)
    window_start = starts_at - timedelta(minutes=90)
    window_end = starts_at + timedelta(minutes=90)
    candidates = db.scalars(
        select(Event)
        .where(
            and_(
                Event.city_id == city.id,
                Event.venue_id == venue.id,
                Event.starts_at >= window_start,
                Event.starts_at <= window_end,
                Event.status != "rejected",
            )
        )
        .limit(20)
    )
    source_title = clean_name(source_event.title)
    source_artist = clean_name(source_event.artist_name or source_event.title)
    for candidate in candidates:
        candidate_title = clean_name(candidate.title)
        candidate_artist = clean_name(candidate.artist.name if candidate.artist else candidate.title)
        if candidate_title == source_title or candidate_artist == source_artist or candidate.artist_id == artist.id:
            return candidate
    return None


def finish_ingestion_run(
    run: IngestionRun,
    status: str,
    failures: int | None = None,
    warnings: list[str] | None = None,
) -> None:
    run.status = status
    if failures is not None:
        run.failures = failures
    if warnings is not None:
        run.warnings = warnings
    run.finished_at = datetime.utcnow()


def json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def ensure_source(db: Session, name: str, kind: str) -> Source:
    source = db.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(
            name=name,
            slug=slugify(name),
            kind=kind,
            is_enabled=name in {"Ticketmaster Discovery API", "Manual CSV import"},
        )
        db.add(source)
        db.flush()
    if not source.slug:
        source.slug = slugify(name)
    return source


def apply_adapter_metadata(source: Source, adapter: EventSourceAdapter) -> None:
    metadata = adapter_metadata(adapter)  # type: ignore[arg-type]
    for key, value in metadata.items():
        if key == "slug" and source.slug:
            continue
        if key == "base_url" and source.base_url:
            continue
        if key == "terms_url" and source.terms_url:
            continue
        if key == "limitations" and source.notes:
            source.limitations = value or source.limitations
            continue
        if hasattr(source, key):
            setattr(source, key, value)
    if not source.notes and metadata.get("limitations"):
        source.notes = metadata["limitations"]


def adapter_configured(db: Session, adapter: EventSourceAdapter) -> bool:
    required_settings = getattr(adapter, "required_settings", [])
    if not required_settings:
        return True
    return all(bool(get_raw_setting(db, key)) for key in required_settings if key != "songkick_partner_mode") and (
        str(get_raw_setting(db, "songkick_partner_mode")).lower() == "true"
        if "songkick_partner_mode" in required_settings
        else True
    )


def find_or_create_artist(db: Session, name: str) -> Artist:
    slug = slugify(name)
    artist = db.scalar(select(Artist).where(Artist.slug == slug))
    if artist is None:
        artist = Artist(name=name, slug=slug)
        db.add(artist)
        db.flush()
    return artist


def find_or_create_venue(
    db: Session,
    city: City,
    venue_whitelist: list[str],
    venue_name: str,
) -> Venue:
    slug = slugify(venue_name)
    venue = db.scalar(select(Venue).where(Venue.city_id == city.id, Venue.slug == slug))
    if venue is None:
        venue = Venue(
            city_id=city.id,
            name=venue_name,
            slug=slug,
            is_whitelisted=slug in venue_whitelist,
            source_notes="Created during ingestion; review venue metadata.",
        )
        db.add(venue)
        db.flush()
    return venue


def get_city_config(city_slug: str):
    from app.cities.registry import get_city_config as registry_get_city_config

    return registry_get_city_config(city_slug)


def default_adapters_for_db(db: Session) -> list[EventSourceAdapter]:
    adapters = get_default_adapters()
    ticketmaster_key = get_raw_setting(db, "ticketmaster_api_key")
    eventbrite_key = get_raw_setting(db, "eventbrite_api_key")
    from app.sources.eventbrite import EventbriteAdapter
    from app.sources.bandsintown import BandsintownAdapter
    from app.sources.skiddle import SkiddleAdapter
    from app.sources.songkick import SongkickAdapter

    configured_adapters: list[EventSourceAdapter] = []
    for adapter in adapters:
        if adapter.name == EventbriteAdapter.name:
            source = ensure_source(db, adapter.name, adapter.kind)
            apply_adapter_metadata(source, adapter)
            if not source.is_enabled or not eventbrite_key:
                continue
            configured_adapters.append(EventbriteAdapter(api_key=eventbrite_key))
            continue
        if adapter.name == BandsintownAdapter.name:
            source = ensure_source(db, adapter.name, adapter.kind)
            apply_adapter_metadata(source, adapter)
            bandsintown_key = get_raw_setting(db, "bandsintown_app_id")
            if not source.is_enabled or not bandsintown_key:
                continue
            configured_adapters.append(
                BandsintownAdapter(
                    app_id=bandsintown_key,
                    artist_seed_list=get_raw_setting(db, "bandsintown_artist_seed_list"),
                )
            )
            continue
        if adapter.name == SkiddleAdapter.name:
            source = ensure_source(db, adapter.name, adapter.kind)
            apply_adapter_metadata(source, adapter)
            skiddle_key = get_raw_setting(db, "skiddle_api_key")
            skiddle_city_id = get_raw_setting(db, "skiddle_city_id")
            skiddle_base_url = get_raw_setting(db, "skiddle_api_base_url")
            if not source.is_enabled or not skiddle_key or not skiddle_city_id or not skiddle_base_url:
                continue
            configured_adapters.append(
                SkiddleAdapter(
                    api_key=skiddle_key,
                    city_id=skiddle_city_id,
                    api_base_url=skiddle_base_url,
                )
            )
            continue
        if adapter.name == SongkickAdapter.name:
            source = ensure_source(db, adapter.name, adapter.kind)
            apply_adapter_metadata(source, adapter)
            songkick_key = get_raw_setting(db, "songkick_api_key")
            partner_mode = str(get_raw_setting(db, "songkick_partner_mode") or "").lower() == "true"
            metro_area_id = get_raw_setting(db, "songkick_metro_area_id")
            if not source.is_enabled or not songkick_key or not partner_mode or not metro_area_id:
                continue
            configured_adapters.append(
                SongkickAdapter(
                    api_key=songkick_key,
                    partner_mode=partner_mode,
                    metro_area_id=metro_area_id,
                )
            )
            continue
        configured_adapters.append(adapter)
    adapters = configured_adapters

    if ticketmaster_key:
        from app.sources.ticketmaster import TicketmasterDiscoveryAdapter

        adapters = [
            TicketmasterDiscoveryAdapter(api_key=ticketmaster_key)
            if adapter.name == TicketmasterDiscoveryAdapter.name
            else adapter
            for adapter in adapters
        ]
    return adapters


def ingestion_log_payload(log: IngestionLog) -> dict:
    return {
        "id": log.id,
        "source_name": log.source_name,
        "city_slug": log.city_slug,
        "events_found": log.events_found,
        "events_created": log.events_created,
        "events_updated": log.events_updated,
        "duplicates_skipped": log.duplicates_skipped,
        "failures": log.failures,
        "warnings": log.warnings or [],
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    }
