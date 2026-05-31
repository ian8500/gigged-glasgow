from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artist import Artist
from app.models.city import City
from app.models.event import Event
from app.models.source import Source
from app.models.venue import Venue
from app.services.normalization import (
    confidence_score,
    ensure_aware,
    event_fingerprint,
    event_slug,
    needs_review,
)
from app.services.seed import seed_glasgow
from app.sources.base import EventSourceAdapter, NormalizedSourceEvent
from app.sources.registry import get_default_adapters


@dataclass(slots=True)
class IngestionReport:
    city: str
    fetched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


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
    end = start + timedelta(days=config.minimum_date_range_days)
    report = IngestionReport(city=city_slug)

    for adapter in adapters or get_default_adapters():
        source = ensure_source(db, adapter.name, adapter.kind)
        result = adapter.fetch(config, start, end)
        report.warnings.extend(result.warnings)
        report.fetched += len(result.events)

        for source_event in result.events:
            created = upsert_event(db, city, config.venue_whitelist, source, source_event)
            if created is None:
                report.skipped += 1
            elif created:
                report.created += 1
            else:
                report.updated += 1

    db.commit()
    return report


def upsert_event(
    db: Session,
    city: City,
    venue_whitelist: list[str],
    source: Source,
    source_event: NormalizedSourceEvent,
) -> bool | None:
    source_event.starts_at = ensure_aware(source_event.starts_at)
    venue = find_or_create_venue(db, city, venue_whitelist, source_event.venue_name)
    artist = find_or_create_artist(db, source_event.artist_name or source_event.title)
    fingerprint = event_fingerprint(city.slug, source_event)
    score = confidence_score(source_event, venue.is_whitelisted)

    event = db.scalar(
        select(Event).where(
            Event.city_id == city.id,
            Event.normalized_fingerprint == fingerprint,
        )
    )
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

    event.venue_id = venue.id
    event.artist_id = artist.id
    event.source_id = source.id
    event.title = source_event.title
    event.slug = event_slug(source_event.title, source_event.starts_at)
    event.starts_at = source_event.starts_at
    event.ends_at = source_event.ends_at
    event.ticket_url = source_event.ticket_url
    event.image_url = source_event.image_url
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
    return created


def ensure_source(db: Session, name: str, kind: str) -> Source:
    source = db.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(name=name, kind=kind, is_enabled=True)
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
