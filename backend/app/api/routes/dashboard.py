from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.city import City
from app.models.event import Event
from app.models.ingestion_log import IngestionLog
from app.models.social_post import SocialPost
from app.models.venue import Venue

router = APIRouter()


@router.get("/summary")
def dashboard_summary(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    city_record = require_city(db, city)
    return {
        "city": city_record.name,
        "counts": {
            "events": count(db, Event, city_record.id),
            "venues": count(db, Venue, city_record.id),
            "social_posts": count(db, SocialPost, city_record.id),
            "needs_review": db.scalar(
                select(func.count(Event.id)).where(
                    Event.city_id == city_record.id,
                    Event.needs_review.is_(True),
                )
            )
            or 0,
        },
        "next_events": [
            event.title
            for event in db.scalars(
                select(Event)
                .where(Event.city_id == city_record.id, Event.starts_at >= datetime.utcnow())
                .order_by(Event.starts_at.asc())
                .limit(8)
            )
        ],
    }


@router.get("/activity")
def dashboard_activity(city: str = "glasgow", limit: int = 20, db: Session = Depends(get_db)) -> dict:
    city_record = require_city(db, city)
    recent_logs = db.scalars(
        select(IngestionLog)
        .where(IngestionLog.city_id == city_record.id)
        .order_by(IngestionLog.started_at.desc())
        .limit(min(limit, 100))
    )
    recent_events = db.scalars(
        select(Event)
        .where(Event.city_id == city_record.id, Event.created_at >= datetime.utcnow() - timedelta(days=14))
        .order_by(Event.created_at.desc())
        .limit(10)
    )
    return {
        "city": city_record.slug,
        "ingestion": [
            {
                "id": log.id,
                "source_name": log.source_name,
                "events_found": log.events_found,
                "events_created": log.events_created,
                "duplicates_skipped": log.duplicates_skipped,
                "failures": log.failures,
                "started_at": log.started_at.isoformat() if log.started_at else None,
            }
            for log in recent_logs
        ],
        "events": [
            {
                "id": event.id,
                "title": event.title,
                "status": event.status,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in recent_events
        ],
    }


def count(db: Session, model, city_id: int) -> int:
    return db.scalar(select(func.count(model.id)).where(model.city_id == city_id)) or 0


def require_city(db: Session, city: str) -> City:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city_record
