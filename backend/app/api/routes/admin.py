from __future__ import annotations

import csv
import io
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_admin
from app.models.artist import Artist
from app.models.city import City
from app.models.event import Event
from app.models.social_post import SocialPost
from app.models.venue import Venue
from app.schemas.event import EventAdminEdit, EventCreate, EventCsvImport, EventRead
from app.schemas.social_post import SocialPostEdit, SocialPostRead
from app.schemas.venue import VenueCreate, VenueRead
from app.services.city_brands import create_city_from_template, city_brand_payload, city_template_payloads
from app.services.deduplication import merge_event
from app.services.ingestion import ensure_source, find_or_create_artist, find_or_create_venue
from app.services.meta_publishing import get_meta_readiness, publish_via_meta_placeholder
from app.services.normalization import event_slug, fingerprint_parts
from app.services.seed import seed_glasgow
from app.services.social_generation import generate_social_posts, regenerate_post
from app.services.venue_coverage import (
    check_venue_now,
    run_all_venue_checks,
    seed_glasgow_venue_coverage,
    venue_coverage_payload,
)
from app.services.weekly import generate_weekly_issue

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/dashboard")
def dashboard(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")

    event_count = db.scalar(select(func.count(Event.id)).where(Event.city_id == city_record.id)) or 0
    venue_count = db.scalar(select(func.count(Venue.id)).where(Venue.city_id == city_record.id)) or 0
    post_count = db.scalar(select(func.count(SocialPost.id)).where(SocialPost.city_id == city_record.id)) or 0
    review_count = (
        db.scalar(
            select(func.count(Event.id)).where(
                Event.city_id == city_record.id,
                Event.needs_review.is_(True),
            )
        )
        or 0
    )

    next_events = list(
        db.scalars(
            select(Event)
            .where(Event.city_id == city_record.id, Event.starts_at >= datetime.utcnow())
            .order_by(Event.starts_at.asc())
            .limit(8)
        )
    )

    return {
        "city": city_record.name,
        "counts": {
            "events": event_count,
            "venues": venue_count,
            "social_posts": post_count,
            "needs_review": review_count,
        },
        "next_events": [event.title for event in next_events],
    }


@router.post("/seed/glasgow")
def seed_glasgow_endpoint(db: Session = Depends(get_db)) -> dict[str, str]:
    seed_glasgow(db)
    return {"status": "seeded", "city": "glasgow"}


@router.get("/venue-coverage")
def venue_coverage(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    try:
        return venue_coverage_payload(db, city)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/venue-coverage/seed/glasgow")
def seed_venue_coverage(db: Session = Depends(get_db)) -> dict:
    try:
        upserted = seed_glasgow_venue_coverage(db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "seeded", "city": "glasgow", "venues_upserted": upserted}


@router.post("/venue-coverage/check-all")
def check_all_venues(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    try:
        return run_all_venue_checks(db, city)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/venues/{venue_id}/check-now")
def check_single_venue(venue_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return asdict(check_venue_now(db, venue_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/city-templates")
def admin_city_templates() -> list[dict]:
    return city_template_payloads()


@router.get("/city-brands")
def admin_city_brands(db: Session = Depends(get_db)) -> list[dict]:
    return [city_brand_payload(city) for city in db.scalars(select(City).order_by(City.name))]


@router.post("/city-brands/{template_slug}")
def create_city_brand(template_slug: str, db: Session = Depends(get_db)) -> dict:
    try:
        city = create_city_from_template(db, template_slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return city_brand_payload(city)


@router.post("/venues", response_model=VenueRead)
def create_venue(payload: VenueCreate, db: Session = Depends(get_db)) -> Venue:
    city = db.scalar(select(City).where(City.slug == payload.city_slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")

    venue = Venue(
        city_id=city.id,
        name=payload.name,
        slug=payload.slug,
        address=payload.address,
        postcode=payload.postcode,
        capacity=payload.capacity,
        website_url=payload.website_url,
        event_listings_url=payload.event_listings_url,
        ticketing_url=payload.ticketing_url,
        instagram_handle=payload.instagram_handle,
        source_discovered_from=payload.source_discovered_from,
        status=payload.status,
        coverage_status=payload.coverage_status,
        notes=payload.notes,
        is_whitelisted=payload.is_whitelisted,
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@router.post("/events", response_model=EventRead)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    city = db.scalar(select(City).where(City.slug == payload.city_slug))
    venue = db.scalar(select(Venue).where(Venue.slug == payload.venue_slug))
    if city is None or venue is None:
        raise HTTPException(status_code=404, detail="City or venue not found")

    event = Event(
        city_id=city.id,
        venue_id=venue.id,
        title=payload.title,
        slug=payload.slug,
        starts_at=payload.starts_at,
        ticket_url=payload.ticket_url,
        genre=payload.genre,
        source_attribution="Manual admin entry",
        confidence_score=1.0,
        needs_review=False,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/events")
def admin_events(
    city: str = "glasgow",
    view: str = "inbox",
    db: Session = Depends(get_db),
) -> list[dict]:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")

    statement = (
        select(Event)
        .where(Event.city_id == city_record.id)
        .options(joinedload(Event.artist), joinedload(Event.venue), joinedload(Event.source))
        .order_by(Event.starts_at.asc())
    )
    if view == "needs-review":
        statement = statement.where(Event.needs_review.is_(True))
    elif view == "approved":
        statement = statement.where(Event.needs_review.is_(False), Event.status == "scheduled")
    elif view == "rejected":
        statement = statement.where(Event.status == "rejected")

    return [event_admin_payload(event) for event in db.scalars(statement)]


@router.patch("/events/{event_id}")
def edit_event(event_id: int, payload: EventAdminEdit, db: Session = Depends(get_db)) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if payload.title is not None:
        event.title = payload.title
        event.slug = event_slug(payload.title, payload.starts_at or event.starts_at)
    if payload.starts_at is not None:
        event.starts_at = payload.starts_at
    if payload.ticket_url is not None:
        event.ticket_url = payload.ticket_url
    if payload.genre is not None:
        event.genre = payload.genre
    if payload.editorial_note is not None:
        event.editorial_note = payload.editorial_note
    if payload.price_min is not None:
        event.price_min = payload.price_min
    if payload.price_max is not None:
        event.price_max = payload.price_max
    if event.artist and event.venue:
        event.normalized_fingerprint = fingerprint_parts(
            event.city.slug,
            event.artist.name,
            event.venue.name,
            event.starts_at,
        )
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{event_id}/approve")
def approve_event(event_id: int, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    event.needs_review = False
    event.status = "scheduled"
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{event_id}/reject")
def reject_event(event_id: int, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    event.status = "rejected"
    event.needs_review = False
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{event_id}/top-pick")
def mark_top_pick(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    metadata = dict(event.raw_payload or {})
    metadata["top_pick"] = enabled
    event.raw_payload = metadata
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{event_id}/sponsored")
def mark_sponsored(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    metadata = dict(event.raw_payload or {})
    metadata["sponsored"] = enabled
    event.raw_payload = metadata
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{keeper_id}/merge/{duplicate_id}")
def merge_duplicate_events(keeper_id: int, duplicate_id: int, db: Session = Depends(get_db)) -> dict:
    keeper = require_event(db, keeper_id)
    duplicate = require_event(db, duplicate_id)
    if keeper.city_id != duplicate.city_id:
        raise HTTPException(status_code=400, detail="Cannot merge events from different cities")
    merge_event(keeper, duplicate)
    db.delete(duplicate)
    db.commit()
    db.refresh(keeper)
    return event_admin_payload(keeper)


@router.post("/events/manual")
def add_manual_event(payload: EventCreate, db: Session = Depends(get_db)) -> dict:
    city = db.scalar(select(City).where(City.slug == payload.city_slug))
    venue = db.scalar(select(Venue).where(Venue.slug == payload.venue_slug))
    if city is None or venue is None:
        raise HTTPException(status_code=404, detail="City or venue not found")
    source = ensure_source(db, "Manual admin entry", "manual")
    artist = find_or_create_artist(db, payload.title)
    fingerprint = fingerprint_parts(city.slug, artist.name, venue.name, payload.starts_at)
    event = Event(
        city_id=city.id,
        venue_id=venue.id,
        artist_id=artist.id,
        source_id=source.id,
        title=payload.title,
        slug=payload.slug or event_slug(payload.title, payload.starts_at),
        starts_at=payload.starts_at,
        ticket_url=payload.ticket_url,
        genre=payload.genre,
        source_attribution="Manual admin entry",
        confidence_score=1.0,
        needs_review=False,
        status="scheduled",
        normalized_fingerprint=fingerprint,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/import-csv")
def import_events_csv(payload: EventCsvImport, db: Session = Depends(get_db)) -> dict:
    city = db.scalar(select(City).where(City.slug == payload.city_slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    source = ensure_source(db, "Manual CSV upload", "manual_csv")
    reader = csv.DictReader(io.StringIO(payload.csv_text))
    created = 0
    for row in reader:
        if not row.get("title") or not row.get("venue_name") or not row.get("starts_at"):
            continue
        starts_at = datetime.fromisoformat(row["starts_at"])
        venue = find_or_create_venue(db, city, [], row["venue_name"])
        artist = find_or_create_artist(db, row.get("artist_name") or row["title"])
        fingerprint = fingerprint_parts(city.slug, artist.name, venue.name, starts_at)
        if db.scalar(select(Event).where(Event.city_id == city.id, Event.normalized_fingerprint == fingerprint)):
            continue
        db.add(
            Event(
                city_id=city.id,
                venue_id=venue.id,
                artist_id=artist.id,
                source_id=source.id,
                title=row["title"],
                slug=event_slug(row["title"], starts_at),
                starts_at=starts_at,
                ticket_url=row.get("ticket_url") or None,
                genre=row.get("genre") or None,
                source_attribution="Manual CSV upload",
                confidence_score=0.85,
                needs_review=True,
                normalized_fingerprint=fingerprint,
                raw_payload=row,
            )
        )
        created += 1
    db.commit()
    return {"created": created}


@router.post("/weekly/generate")
def generate_weekly(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    report = generate_weekly_issue(db, city)
    return {
        "city": report.city,
        "issue_slug": report.issue_slug,
        "events_selected": report.events_selected,
        "post_created": report.post_created,
        "coverage_report": report.coverage_report,
    }


@router.post("/social/generate")
def generate_social_queue(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    report = generate_social_posts(db, city)
    return {"city": report.city, "generated": report.generated, "post_ids": report.post_ids}


@router.get("/social/review-queue", response_model=list[SocialPostRead])
def social_review_queue(
    city: str = "glasgow",
    status: str = "review",
    db: Session = Depends(get_db),
) -> list[SocialPost]:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")
    return list(
        db.scalars(
            select(SocialPost)
            .where(SocialPost.city_id == city_record.id, SocialPost.status == status)
            .order_by(SocialPost.created_at.desc())
        )
    )


@router.patch("/social/{post_id}", response_model=SocialPostRead)
def edit_social_post(
    post_id: int,
    payload: SocialPostEdit,
    db: Session = Depends(get_db),
) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")

    preview = dict(post.preview_payload or {})
    if payload.caption is not None:
        post.caption = payload.caption
        preview["caption"] = payload.caption
    if payload.title is not None:
        preview["title"] = payload.title
    if payload.description is not None:
        preview["description"] = payload.description
        post.image_prompt = payload.description
    if payload.hashtags is not None:
        preview["hashtags"] = payload.hashtags
    if payload.status is not None:
        post.status = payload.status
        preview["status"] = payload.status

    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


@router.post("/social/{post_id}/approve", response_model=SocialPostRead)
def approve_social_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    return set_social_status(db, post_id, "approved")


@router.post("/social/{post_id}/reject", response_model=SocialPostRead)
def reject_social_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    return set_social_status(db, post_id, "rejected")


@router.post("/social/{post_id}/schedule", response_model=SocialPostRead)
def schedule_social_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    if post.status not in {"approved", "scheduled"}:
        raise HTTPException(status_code=400, detail="Only approved posts can be scheduled.")
    preview = dict(post.preview_payload or {})
    preview["status"] = "scheduled"
    preview["publishing"] = {
        **dict(preview.get("publishing") or {}),
        "auto_publish": False,
        "mode": "manual_export",
    }
    post.status = "scheduled"
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


@router.get("/instagram/settings")
def instagram_settings() -> dict:
    readiness = get_meta_readiness()
    return {
        "ready": readiness.ready,
        "reason": readiness.reason,
        "required_permissions": readiness.required_permissions,
        "account_type": readiness.account_type,
        "safe_fallback": "Export PNG plus caption and post manually.",
    }


@router.post("/social/{post_id}/meta-placeholder")
def meta_publish_placeholder(post_id: int, db: Session = Depends(get_db)) -> dict:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    result = publish_via_meta_placeholder(post)
    if result["published"]:
        post.status = "published"
    else:
        post.status = "failed" if result["status"] == "placeholder_error" else post.status
    db.commit()
    return result


@router.post("/social/{post_id}/regenerate", response_model=SocialPostRead)
def regenerate_social_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    try:
        return regenerate_post(db, post)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def set_social_status(db: Session, post_id: int, status: str) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    preview = dict(post.preview_payload or {})
    post.status = status
    preview["status"] = status
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


def require_event(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def event_admin_payload(event: Event) -> dict:
    metadata = event.raw_payload or {}
    return {
        "id": event.id,
        "title": event.title,
        "artist": event.artist.name if event.artist else event.title,
        "venue": event.venue.name if event.venue else "Venue TBC",
        "venue_slug": event.venue.slug if event.venue else None,
        "starts_at": event.starts_at.isoformat(),
        "ticket_url": event.ticket_url,
        "genre": event.genre,
        "price_min": str(event.price_min) if event.price_min is not None else None,
        "price_max": str(event.price_max) if event.price_max is not None else None,
        "status": event.status,
        "needs_review": event.needs_review,
        "confidence_score": event.confidence_score,
        "source_attribution": event.source_attribution,
        "editorial_note": event.editorial_note,
        "top_pick": bool(metadata.get("top_pick")),
        "sponsored": bool(metadata.get("sponsored")),
    }
