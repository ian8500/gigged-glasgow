from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.city import City
from app.models.venue import Venue
from app.schemas.venue import VenueCreate, VenueRead, VenueUpdate
from app.services.venue_coverage import check_venue_now, run_all_venue_checks

router = APIRouter()


@router.get("", response_model=list[VenueRead])
def list_venues(city: str = "glasgow", db: Session = Depends(get_db)) -> list[Venue]:
    statement = (
        select(Venue)
        .join(City)
        .where(City.slug == city)
        .order_by(Venue.is_whitelisted.desc(), Venue.name)
    )
    return list(db.scalars(statement))


@router.post("", response_model=VenueRead, dependencies=[Depends(require_admin)])
def create_venue(payload: VenueCreate, db: Session = Depends(get_db)) -> Venue:
    city = db.scalar(select(City).where(City.slug == payload.city_slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    values = payload.model_dump(exclude={"city_slug"})
    values["official_website_url"] = values.get("official_website_url") or values.get("website_url")
    values["official_events_url"] = values.get("official_events_url") or values.get("event_listings_url")
    venue = Venue(city_id=city.id, **values)
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@router.post("/bulk-check", dependencies=[Depends(require_admin)])
def bulk_check_venues(city: str = "glasgow", live_http: bool = False, db: Session = Depends(get_db)) -> dict:
    try:
        return run_all_venue_checks(db, city, live_http=live_http)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "fix": "Run python manage.py seed, then retry the venue coverage check."}) from exc


@router.get("/{venue_id}", response_model=VenueRead)
def get_venue(venue_id: int, db: Session = Depends(get_db)) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.patch("/{venue_id}", response_model=VenueRead, dependencies=[Depends(require_admin)])
def update_venue(venue_id: int, payload: VenueUpdate, db: Session = Depends(get_db)) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    values = payload.model_dump(exclude_unset=True)
    if values.get("website_url") and "official_website_url" not in values:
        values["official_website_url"] = values["website_url"]
    if values.get("event_listings_url") and "official_events_url" not in values:
        values["official_events_url"] = values["event_listings_url"]
    for key, value in values.items():
        setattr(venue, key, value)
    db.commit()
    db.refresh(venue)
    return venue


@router.delete("/{venue_id}", dependencies=[Depends(require_admin)])
def delete_venue(venue_id: int, db: Session = Depends(get_db)) -> dict:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    db.delete(venue)
    db.commit()
    return {"deleted": True, "venue_id": venue_id}


@router.post("/{venue_id}/check", dependencies=[Depends(require_admin)])
def check_venue(venue_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return asdict(check_venue_now(db, venue_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{venue_id}/mark-manual-only", response_model=VenueRead, dependencies=[Depends(require_admin)])
def mark_venue_manual_only(venue_id: int, db: Session = Depends(get_db)) -> Venue:
    venue = get_venue(venue_id, db)
    venue.coverage_status = "manual_only"
    venue.source_mode = "manual_only"
    venue.notes = append_note(venue.notes, "Marked manual-only from coverage dashboard.")
    db.commit()
    db.refresh(venue)
    return venue


@router.post("/{venue_id}/mark-checked", response_model=VenueRead, dependencies=[Depends(require_admin)])
def mark_venue_checked(venue_id: int, db: Session = Depends(get_db)) -> Venue:
    venue = get_venue(venue_id, db)
    now = datetime.utcnow()
    venue.last_checked_at = now
    venue.notes = append_note(venue.notes, "Marked checked manually from coverage dashboard.")
    for source in venue.coverage_sources:
        source.last_checked_at = now
    db.commit()
    db.refresh(venue)
    return venue


@router.post("/{venue_id}/mark-source-broken", response_model=VenueRead, dependencies=[Depends(require_admin)])
def mark_venue_source_broken(venue_id: int, db: Session = Depends(get_db)) -> Venue:
    venue = get_venue(venue_id, db)
    venue.coverage_status = "broken"
    venue.last_error = "Marked source broken from coverage dashboard."
    venue.structure_changed = True
    venue.notes = append_note(venue.notes, "Marked source broken from coverage dashboard.")
    for source in venue.coverage_sources:
        source.status = "broken"
    db.commit()
    db.refresh(venue)
    return venue


@router.post("/{keeper_id}/merge/{duplicate_id}", response_model=VenueRead, dependencies=[Depends(require_admin)])
def merge_venues(keeper_id: int, duplicate_id: int, db: Session = Depends(get_db)) -> Venue:
    keeper = get_venue(keeper_id, db)
    duplicate = get_venue(duplicate_id, db)
    if keeper.city_id != duplicate.city_id:
        raise HTTPException(status_code=400, detail="Cannot merge venues from different cities")
    for event in duplicate.events:
        event.venue_id = keeper.id
    keeper.notes = append_note(keeper.notes, f"Merged duplicate venue: {duplicate.name}.")
    duplicate.status = "duplicate"
    db.commit()
    db.refresh(keeper)
    return keeper


def append_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing}\n{note}"
