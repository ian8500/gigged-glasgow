from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.promoter_submission import PromoterSubmission
from app.models.city import City
from app.models.event import Event
from app.services.ingestion import ensure_source, find_or_create_artist, find_or_create_venue
from app.services.normalization import event_slug, fingerprint_parts

router = APIRouter()


class SubmissionCreate(BaseModel):
    event_title: str
    artist: str
    venue: str
    date: str
    time: str
    ticket_url: str
    price: Decimal | None = None
    promoter_contact_email: str
    image_upload_url: str | None = None
    notes: str | None = None
    city_slug: str = "glasgow"


@router.post("")
def create_submission(payload: SubmissionCreate, db: Session = Depends(get_db)) -> dict:
    submission = PromoterSubmission(
        city_slug=payload.city_slug,
        event_title=payload.event_title,
        artist=payload.artist,
        venue=payload.venue,
        event_date=payload.date,
        event_time=payload.time,
        ticket_url=payload.ticket_url,
        price=payload.price,
        promoter_contact_email=str(payload.promoter_contact_email),
        image_upload_url=payload.image_upload_url,
        notes=payload.notes,
    )
    db.add(submission)
    db.commit()
    return {"ok": True, "status": "pending", "id": submission.id}


@router.get("", dependencies=[Depends(require_admin)])
def list_submissions(status: str = "pending", db: Session = Depends(get_db)) -> list[dict]:
    statement = select(PromoterSubmission).order_by(PromoterSubmission.created_at.desc())
    if status != "all":
        statement = statement.where(PromoterSubmission.status == status)
    return [submission_payload(row) for row in db.scalars(statement)]


@router.post("/{submission_id}/approve", dependencies=[Depends(require_admin)])
def approve_submission(submission_id: int, db: Session = Depends(get_db)) -> dict:
    submission = require_submission(db, submission_id)
    city = db.scalar(select(City).where(City.slug == submission.city_slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    starts_at = datetime.fromisoformat(f"{submission.event_date}T{submission.event_time}")
    source = ensure_source(db, "Promoter submissions", "manual")
    venue = find_or_create_venue(db, city, [], submission.venue)
    artist = find_or_create_artist(db, submission.artist)
    event = Event(
        city_id=city.id,
        venue_id=venue.id,
        artist_id=artist.id,
        source_id=source.id,
        title=submission.event_title,
        slug=event_slug(submission.event_title, starts_at),
        starts_at=starts_at,
        ticket_url=submission.ticket_url,
        image_url=submission.image_upload_url,
        price_min=submission.price,
        price_max=submission.price,
        source_attribution="Promoter submission",
        normalized_fingerprint=fingerprint_parts(city.slug, submission.event_title, submission.venue, starts_at),
        confidence_score=0.7,
        needs_review=True,
        raw_payload=submission_payload(submission),
    )
    db.add(event)
    submission.status = "approved"
    submission.reviewed_at = datetime.utcnow()
    db.flush()
    submission.created_event_id = event.id
    db.commit()
    return submission_payload(submission)


@router.post("/{submission_id}/reject", dependencies=[Depends(require_admin)])
def reject_submission(submission_id: int, db: Session = Depends(get_db)) -> dict:
    submission = require_submission(db, submission_id)
    submission.status = "rejected"
    submission.reviewed_at = datetime.utcnow()
    db.commit()
    return submission_payload(submission)


def require_submission(db: Session, submission_id: int) -> PromoterSubmission:
    submission = db.get(PromoterSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


def submission_payload(submission: PromoterSubmission) -> dict:
    return {
        "id": submission.id,
        "city_slug": submission.city_slug,
        "event_title": submission.event_title,
        "artist": submission.artist,
        "venue": submission.venue,
        "date": submission.event_date,
        "time": submission.event_time,
        "ticket_url": submission.ticket_url,
        "price": str(submission.price) if submission.price is not None else None,
        "promoter_contact_email": submission.promoter_contact_email,
        "image_upload_url": submission.image_upload_url,
        "notes": submission.notes,
        "status": submission.status,
        "created_event_id": submission.created_event_id,
        "created_at": submission.created_at.isoformat() if submission.created_at else None,
        "reviewed_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
    }
