from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.source_feed import SourceFeed
from app.services.ingestion import ingest_city
from app.sources.base import SourceAdapterBase
from app.sources.feed import fetch_feed_events

router = APIRouter(dependencies=[Depends(require_admin)])


class FeedCreate(BaseModel):
    source_name: str
    city_slug: str = "glasgow"
    feed_url: str
    feed_type: str
    venue_id: int | None = None
    notes: str | None = None


class FeedUpdate(BaseModel):
    enabled: bool | None = None
    notes: str | None = None


@router.get("")
def list_feeds(city: str = "glasgow", db: Session = Depends(get_db)) -> list[dict]:
    feeds = db.scalars(select(SourceFeed).where(SourceFeed.city_slug == city).order_by(SourceFeed.id.desc()))
    return [feed_payload(feed) for feed in feeds]


@router.post("")
def create_feed(payload: FeedCreate, db: Session = Depends(get_db)) -> dict:
    if payload.feed_type not in {"rss", "atom", "ical"}:
        raise HTTPException(status_code=400, detail="feed_type must be rss, atom, or ical")
    feed = SourceFeed(**payload.model_dump())
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed_payload(feed)


@router.patch("/{feed_id}")
def update_feed(feed_id: int, payload: FeedUpdate, db: Session = Depends(get_db)) -> dict:
    feed = db.get(SourceFeed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(feed, key, value)
    db.commit()
    db.refresh(feed)
    return feed_payload(feed)


@router.delete("/{feed_id}")
def delete_feed(feed_id: int, db: Session = Depends(get_db)) -> dict:
    feed = db.get(SourceFeed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    db.delete(feed)
    db.commit()
    return {"ok": True}


@router.post("/{feed_id}/test")
def test_feed(feed_id: int, db: Session = Depends(get_db)) -> dict:
    feed = require_feed(db, feed_id)
    result = fetch_feed_events(feed.feed_url, feed.feed_type, feed.source_name)
    feed.last_checked_at = datetime.utcnow()
    if result.failures:
        feed.last_error = "; ".join(result.failures)
    else:
        feed.last_error = None
        feed.last_success_at = datetime.utcnow()
    db.commit()
    return {"ok": not result.failures, "events_found": len(result.events), "warnings": result.warnings, "failures": result.failures}


@router.post("/{feed_id}/run")
def run_feed(feed_id: int, db: Session = Depends(get_db)) -> dict:
    feed = require_feed(db, feed_id)
    if not feed.enabled:
        raise HTTPException(status_code=400, detail="Feed is disabled")
    adapter = FeedAdapter(feed)
    report = ingest_city(db, feed.city_slug, adapters=[adapter])
    feed.last_checked_at = datetime.utcnow()
    if report.failures:
        feed.last_error = "; ".join(report.warnings)
    else:
        feed.last_error = None
        feed.last_success_at = datetime.utcnow()
    db.commit()
    return {
        "city": report.city,
        "events_found": report.fetched,
        "events_created": report.created,
        "events_updated": report.updated,
        "duplicates_skipped": report.skipped,
        "failures": report.failures,
        "warnings": report.warnings,
        "logs": report.source_logs,
    }


def require_feed(db: Session, feed_id: int) -> SourceFeed:
    feed = db.get(SourceFeed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


def feed_payload(feed: SourceFeed) -> dict:
    return {
        "id": feed.id,
        "source_name": feed.source_name,
        "venue_id": feed.venue_id,
        "city_slug": feed.city_slug,
        "feed_url": feed.feed_url,
        "feed_type": feed.feed_type,
        "enabled": feed.enabled,
        "last_checked_at": feed.last_checked_at.isoformat() if feed.last_checked_at else None,
        "last_success_at": feed.last_success_at.isoformat() if feed.last_success_at else None,
        "last_error": feed.last_error,
        "notes": feed.notes,
    }


class FeedAdapter(SourceAdapterBase):
    def __init__(self, feed: SourceFeed) -> None:
        self.feed = feed
        self.name = feed.source_name
        self.slug = f"feed-{feed.id}"
        self.kind = "ical" if feed.feed_type == "ical" else "rss"
        self.current_mode = "working"
        self.limitations = "Public feed ingestion; low-confidence rows go to review."

    def fetch_events(self, city, start: datetime, end: datetime):
        result = fetch_feed_events(self.feed.feed_url, self.feed.feed_type, self.feed.source_name)
        result.events = [event for event in result.events if start <= event.starts_at <= end]
        return result
