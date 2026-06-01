from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_admin
from app.models.city import City
from app.models.event import Event
from app.models.venue import Venue
from app.schemas.event import EventAdminEdit, EventCreate, EventRead
from app.services.deduplication import dedupe_city
from app.services.ingestion import ensure_source, find_or_create_artist
from app.services.normalization import event_slug, fingerprint_parts

router = APIRouter()


@router.get("", response_model=list[EventRead])
def list_events(
    city: str = "glasgow",
    upcoming_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[Event]:
    statement = (
        select(Event)
        .join(City)
        .options(joinedload(Event.venue), joinedload(Event.artist), joinedload(Event.source))
        .where(City.slug == city)
        .order_by(Event.starts_at.asc())
        .limit(min(limit, 100))
    )
    if upcoming_only:
        statement = statement.where(Event.starts_at >= datetime.now(timezone.utc))
    return list(db.scalars(statement))


@router.post("", response_model=EventRead, dependencies=[Depends(require_admin)])
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    city = db.scalar(select(City).where(City.slug == payload.city_slug))
    venue = db.scalar(select(Venue).where(Venue.slug == payload.venue_slug))
    if city is None or venue is None:
        raise HTTPException(status_code=404, detail="City or venue not found")
    source = ensure_source(db, "Manual admin entry", "manual")
    artist = find_or_create_artist(db, payload.title)
    event = Event(
        city_id=city.id,
        venue_id=venue.id,
        artist_id=artist.id,
        source_id=source.id,
        title=payload.title,
        slug=payload.slug or event_slug(payload.title, payload.starts_at),
        starts_at=payload.starts_at,
        ticket_url=payload.ticket_url,
        source_url=payload.ticket_url,
        genre=payload.genre,
        source_attribution="Manual admin entry",
        confidence_score=1.0,
        needs_review=False,
        status="scheduled",
        normalized_fingerprint=fingerprint_parts(city.slug, payload.title, venue.name, payload.starts_at),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/dedupe", dependencies=[Depends(require_admin)])
def dedupe_events(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    report = dedupe_city(db, city)
    return {
        "city": report.city,
        "reviewed": report.reviewed,
        "merged": report.merged,
        "marked_for_review": report.marked_for_review,
        "updated_fingerprints": report.updated_fingerprints,
    }


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventRead, dependencies=[Depends(require_admin)])
def update_event(event_id: int, payload: EventAdminEdit, db: Session = Depends(get_db)) -> Event:
    event = require_event(db, event_id)
    values = payload.model_dump(exclude_unset=True)
    venue_slug = values.pop("venue_slug", None)
    if venue_slug:
        venue = db.scalar(select(Venue).where(Venue.city_id == event.city_id, Venue.slug == venue_slug))
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")
        event.venue_id = venue.id
    for key, value in values.items():
        setattr(event, key, value)
    if payload.title or payload.starts_at:
        event.slug = event_slug(event.title, event.starts_at)
    if event.venue:
        event.normalized_fingerprint = fingerprint_parts(
            event.city.slug,
            event.title,
            event.venue.name,
            event.starts_at,
        )
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", dependencies=[Depends(require_admin)])
def delete_event(event_id: int, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    db.delete(event)
    db.commit()
    return {"deleted": True, "event_id": event_id}


@router.post("/{event_id}/approve", response_model=EventRead, dependencies=[Depends(require_admin)])
def approve_event(event_id: int, db: Session = Depends(get_db)) -> Event:
    event = require_event(db, event_id)
    event.needs_review = False
    event.status = "scheduled"
    event.duplicate_of_event_id = None
    event.duplicate_reason = None
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/reject", response_model=EventRead, dependencies=[Depends(require_admin)])
def reject_event(event_id: int, db: Session = Depends(get_db)) -> Event:
    event = require_event(db, event_id)
    event.needs_review = False
    event.status = "rejected"
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/mark-top-pick", response_model=EventRead, dependencies=[Depends(require_admin)])
def mark_top_pick(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> Event:
    event = require_event(db, event_id)
    metadata = dict(event.raw_payload or {})
    metadata["top_pick"] = enabled
    event.raw_payload = metadata
    event.featured = enabled
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/featured", response_model=EventRead, dependencies=[Depends(require_admin)])
def mark_featured(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> Event:
    event = require_event(db, event_id)
    event.featured = enabled
    metadata = dict(event.raw_payload or {})
    metadata["top_pick"] = enabled
    event.raw_payload = metadata
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/instagram-suitable", response_model=EventRead, dependencies=[Depends(require_admin)])
def mark_instagram_suitable(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> Event:
    event = require_event(db, event_id)
    event.instagram_suitable = enabled
    db.commit()
    db.refresh(event)
    return event


def require_event(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
