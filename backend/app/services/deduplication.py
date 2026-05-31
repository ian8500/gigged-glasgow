from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.city import City
from app.models.event import Event
from app.services.normalization import fingerprint_parts


@dataclass(slots=True)
class DedupeReport:
    city: str
    reviewed: int = 0
    merged: int = 0
    updated_fingerprints: int = 0


def dedupe_city(db: Session, city_slug: str) -> DedupeReport:
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise ValueError(f"City '{city_slug}' has not been seeded.")

    events = list(
        db.scalars(
            select(Event)
            .where(Event.city_id == city.id)
            .options(joinedload(Event.artist), joinedload(Event.venue))
        )
    )
    report = DedupeReport(city=city_slug, reviewed=len(events))
    groups: dict[str, list[Event]] = {}

    for event in events:
        artist_name = event.artist.name if event.artist else event.title
        venue_name = event.venue.name if event.venue else "Venue TBC"
        fingerprint = fingerprint_parts(city.slug, artist_name, venue_name, event.starts_at)
        groups.setdefault(fingerprint, []).append(event)

    for fingerprint, duplicate_events in groups.items():
        if len(duplicate_events) == 1:
            event = duplicate_events[0]
            if event.normalized_fingerprint != fingerprint:
                event.normalized_fingerprint = fingerprint
                report.updated_fingerprints += 1
            continue

        keeper = max(
            duplicate_events,
            key=lambda item: (
                item.confidence_score or 0,
                bool(item.ticket_url),
                bool(item.source_event_id),
            ),
        )
        for duplicate in duplicate_events:
            if duplicate.id == keeper.id:
                continue
            merge_event(keeper, duplicate)
            db.delete(duplicate)
            report.merged += 1
        db.flush()
        if keeper.normalized_fingerprint != fingerprint:
            keeper.normalized_fingerprint = fingerprint
            report.updated_fingerprints += 1

    db.commit()
    return report


def merge_event(keeper: Event, duplicate: Event) -> None:
    keeper.ticket_url = keeper.ticket_url or duplicate.ticket_url
    keeper.image_url = keeper.image_url or duplicate.image_url
    keeper.price_min = keeper.price_min or duplicate.price_min
    keeper.price_max = keeper.price_max or duplicate.price_max
    keeper.genre = keeper.genre or duplicate.genre
    keeper.source_event_id = keeper.source_event_id or duplicate.source_event_id
    if duplicate.source_attribution not in keeper.source_attribution:
        keeper.source_attribution = f"{keeper.source_attribution}; {duplicate.source_attribution}"
    keeper.confidence_score = max(keeper.confidence_score or 0, duplicate.confidence_score or 0)
    keeper.needs_review = keeper.needs_review or duplicate.needs_review
