from __future__ import annotations

import csv
import io
from dataclasses import asdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_admin
from app.models.city import City
from app.models.event import Event
from app.models.ingestion_log import IngestionLog
from app.models.social_post import SocialPost
from app.models.venue import Venue
from app.models.weekly_issue import WeeklyIssue
from app.schemas.event import EventAdminEdit, EventCreate, EventCsvImport, EventRead
from app.schemas.social_post import SocialPostEdit, SocialPostRead
from app.schemas.venue import VenueCreate, VenueRead
from app.services.city_brands import create_city_from_template, city_brand_payload, city_template_payloads
from app.services.deduplication import merge_event
from app.services.ingestion import (
    ensure_source,
    find_or_create_artist,
    find_or_create_venue,
    ingest_city,
    ingestion_log_payload,
)
from app.services.meta_publishing import get_meta_readiness, publish_via_meta_placeholder
from app.services.normalization import event_slug, fingerprint_parts
from app.services.seed import seed_glasgow
from app.services.social_generation import export_post_assets, generate_social_posts, regenerate_post
from app.services.venue_coverage import (
    check_venue_now,
    run_all_venue_checks,
    seed_glasgow_venue_coverage,
    venue_coverage_payload,
)
from app.services.weekly import generate_weekly_issue
from app.services.weekly_run import run_weekly_issue_workflow
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter

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


@router.post("/ingest/ticketmaster")
def run_ticketmaster_ingest(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    if city != "glasgow":
        raise HTTPException(status_code=400, detail="Ticketmaster Phase 1 only supports Glasgow")
    report = ingest_city(db, city, adapters=[TicketmasterDiscoveryAdapter()])
    return {
        "city": report.city,
        "source": "Ticketmaster Discovery API",
        "events_found": report.fetched,
        "events_created": report.created,
        "events_updated": report.updated,
        "duplicates_skipped": report.skipped,
        "failures": report.failures,
        "warnings": report.warnings,
        "logs": report.source_logs,
    }


@router.get("/ingest/logs")
def ingest_logs(
    city: str = "glasgow",
    source_name: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = (
        select(IngestionLog)
        .where(IngestionLog.city_slug == city)
    )
    if source_name:
        statement = statement.where(IngestionLog.source_name == source_name)
    statement = statement.order_by(IngestionLog.started_at.desc()).limit(min(limit, 200))
    return [ingestion_log_payload(log) for log in db.scalars(statement)]


@router.get("/venue-coverage")
def venue_coverage(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    try:
        return venue_coverage_payload(db, city)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "fix": "Run python manage.py seed or POST /api/v1/admin/seed/glasgow."}) from exc


@router.post("/venue-coverage/seed/glasgow")
def seed_venue_coverage(db: Session = Depends(get_db)) -> dict:
    try:
        upserted = seed_glasgow_venue_coverage(db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc), "fix": "Run python manage.py seed first."}) from exc
    return {"status": "seeded", "city": "glasgow", "venues_upserted": upserted}


@router.post("/venue-coverage/check-all")
def check_all_venues(city: str = "glasgow", live_http: bool = False, db: Session = Depends(get_db)) -> dict:
    try:
        return run_all_venue_checks(db, city, live_http=live_http)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "fix": "Run python manage.py seed, then retry the venue coverage check."}) from exc


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
        official_website_url=payload.official_website_url or payload.website_url,
        event_listings_url=payload.event_listings_url,
        ticketing_url=payload.ticketing_url,
        official_events_url=payload.official_events_url or payload.event_listings_url,
        feed_url=payload.feed_url,
        source_mode=payload.source_mode,
        selector_config=payload.selector_config,
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
    if view in {"needs-review", "pending"}:
        statement = statement.where(Event.needs_review.is_(True))
    elif view == "approved":
        statement = statement.where(Event.needs_review.is_(False), Event.status == "scheduled")
    elif view == "rejected":
        statement = statement.where(Event.status == "rejected")
    elif view == "imported":
        statement = statement.where(Event.source_attribution != "Manual admin entry")

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
    if payload.venue_slug is not None:
        venue = db.scalar(select(Venue).where(Venue.city_id == event.city_id, Venue.slug == payload.venue_slug))
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")
        event.venue_id = venue.id
    if payload.ticket_url is not None:
        event.ticket_url = payload.ticket_url
    if payload.image_url is not None:
        event.image_url = payload.image_url
    if payload.genre is not None:
        event.genre = payload.genre
    if payload.editorial_note is not None:
        event.editorial_note = payload.editorial_note
    if payload.price_min is not None:
        event.price_min = payload.price_min
    if payload.price_max is not None:
        event.price_max = payload.price_max
    if payload.featured is not None:
        event.featured = payload.featured
    if payload.instagram_suitable is not None:
        event.instagram_suitable = payload.instagram_suitable
    if event.artist and event.venue:
        event.normalized_fingerprint = fingerprint_parts(
            event.city.slug,
            event.title,
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
    event.duplicate_of_event_id = None
    event.duplicate_reason = None
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
    event.featured = enabled
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{event_id}/featured")
def mark_featured(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    event.featured = enabled
    metadata = dict(event.raw_payload or {})
    metadata["top_pick"] = enabled
    event.raw_payload = metadata
    db.commit()
    db.refresh(event)
    return event_admin_payload(event)


@router.post("/events/{event_id}/instagram-suitable")
def mark_instagram_suitable(event_id: int, enabled: bool = True, db: Session = Depends(get_db)) -> dict:
    event = require_event(db, event_id)
    event.instagram_suitable = enabled
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
    fingerprint = fingerprint_parts(city.slug, payload.title, venue.name, payload.starts_at)
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
        fingerprint = fingerprint_parts(city.slug, row["title"], venue.name, starts_at)
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
        "pre_publish_report": report.pre_publish_report,
    }


@router.get("/weekly-run")
def weekly_run_dashboard(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")

    latest_issue = db.scalar(
        select(WeeklyIssue)
        .where(WeeklyIssue.city_id == city_record.id)
        .order_by(WeeklyIssue.generated_at.desc().nullslast(), WeeklyIssue.created_at.desc())
        .limit(1)
    )
    review_posts = list(
        db.scalars(
            select(SocialPost)
            .where(SocialPost.city_id == city_record.id, SocialPost.status.in_(["needs_review", "review"]))
            .order_by(SocialPost.created_at.desc())
        )
    )
    return {
        "title": "Weekly Run",
        "city": city_record.slug,
        "latest_issue": weekly_issue_payload(latest_issue) if latest_issue else None,
        "review_queue_count": len(review_posts),
        "review_queue": [social_post_payload(post) for post in review_posts],
        "actions": {
            "run": "/api/v1/admin/weekly-run/run",
            "approve": "/api/v1/admin/social/{post_id}/approve",
            "edit": "/api/v1/admin/social/{post_id}",
            "regenerate": "/api/v1/admin/social/{post_id}/regenerate",
            "export": "/api/v1/admin/social/{post_id}/export",
            "reject": "/api/v1/admin/social/{post_id}/reject",
            "copy_caption": "/api/v1/admin/social/{post_id}/copy/caption",
            "copy_hashtags": "/api/v1/admin/social/{post_id}/copy/hashtags",
            "calendar": "/api/v1/admin/social/calendar",
            "media_library": "/api/v1/admin/social/media-library",
        },
    }


@router.post("/weekly-run/run")
def run_weekly_run(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    try:
        report = run_weekly_issue_workflow(db, city)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "city": report.city,
        "issue_id": report.issue_id,
        "issue_slug": report.issue_slug,
        "ingest": report.ingest,
        "venue_coverage": report.venue_coverage,
        "dedupe": report.dedupe,
        "candidate_events": report.candidates,
        "posts_created": report.posts_created,
        "review_queue_count": report.review_queue_count,
        "auto_publish": False,
        "safe_to_publish": report.safe_to_publish,
    }


@router.post("/social/generate")
def generate_social_queue(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    report = generate_social_posts(db, city)
    return {"city": report.city, "generated": report.generated, "post_ids": report.post_ids}


@router.get("/social/review-queue", response_model=list[SocialPostRead])
def social_review_queue(
    city: str = "glasgow",
    status: str = "needs_review",
    db: Session = Depends(get_db),
) -> list[SocialPost]:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")
    statuses = ["needs_review", "review"] if status == "needs_review" else [status]
    return list(
        db.scalars(
            select(SocialPost)
            .where(SocialPost.city_id == city_record.id, SocialPost.status.in_(statuses))
            .order_by(SocialPost.created_at.desc())
        )
    )


@router.get("/social/calendar")
def social_calendar(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    posts = list(
        db.scalars(
            select(SocialPost)
            .where(
                SocialPost.city_id == city_record.id,
                SocialPost.planned_for >= start,
                SocialPost.planned_for < end,
            )
            .order_by(SocialPost.planned_for.asc(), SocialPost.created_at.asc())
        )
    )
    return {
        "city": city_record.slug,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "posts": [social_post_payload(post) for post in posts],
    }


@router.get("/social/media-library")
def social_media_library(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    city_record = db.scalar(select(City).where(City.slug == city))
    if city_record is None:
        raise HTTPException(status_code=404, detail="City not found")
    posts = list(
        db.scalars(
            select(SocialPost)
            .where(SocialPost.city_id == city_record.id)
            .order_by(SocialPost.created_at.desc())
            .limit(100)
        )
    )
    media = []
    for post in posts:
        exports = (post.preview_payload or {}).get("exports", {})
        if not exports:
            continue
        media.append(
            {
                "post_id": post.id,
                "template_name": post.template_name,
                "status": post.status,
                "planned_for": post.planned_for.isoformat() if post.planned_for else None,
                "square_png_path": exports.get("square_png_path"),
                "carousel_png_paths": exports.get("carousel_png_paths") or exports.get("png_paths", []),
                "json_path": exports.get("json_path"),
                "alt_text": (post.preview_payload or {}).get("alt_text"),
            }
        )
    return {"city": city_record.slug, "media": media}


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
    if post.status not in {"approved", "exported"}:
        raise HTTPException(status_code=400, detail="Only approved or exported posts can be marked for manual posting.")
    preview = dict(post.preview_payload or {})
    preview["status"] = "exported"
    preview["publishing"] = {
        **dict(preview.get("publishing") or {}),
        "auto_publish": False,
        "mode": "manual_export",
    }
    post.status = "exported"
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


@router.post("/social/{post_id}/export")
def export_social_post(post_id: int, db: Session = Depends(get_db)) -> dict:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    try:
        exports = export_post_assets(post)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    post.status = "exported"
    post.exported_at = datetime.utcnow()
    preview = dict(post.preview_payload or {})
    preview["status"] = "exported"
    post.preview_payload = preview
    db.commit()
    return {"post_id": post.id, "status": post.status, "exports": exports, "auto_publish": False}


@router.post("/social/{post_id}/posted-manually", response_model=SocialPostRead)
def mark_social_post_posted_manually(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    post.status = "posted_manually"
    post.posted_manually_at = datetime.utcnow()
    preview = dict(post.preview_payload or {})
    preview["status"] = "posted_manually"
    preview["publishing"] = {
        **dict(preview.get("publishing") or {}),
        "auto_publish": False,
        "mode": "manual_export",
        "posted_manually_at": post.posted_manually_at.isoformat(),
    }
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


@router.get("/social/{post_id}/copy/caption")
def copy_social_caption(post_id: int, db: Session = Depends(get_db)) -> dict:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    return {"post_id": post.id, "copy_text": post.caption or "", "button_label": "Copy caption"}


@router.get("/social/{post_id}/copy/hashtags")
def copy_social_hashtags(post_id: int, db: Session = Depends(get_db)) -> dict:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    hashtags = (post.preview_payload or {}).get("hashtags", [])
    return {"post_id": post.id, "copy_text": " ".join(hashtags), "button_label": "Copy hashtags"}


@router.get("/social/{post_id}/copy/alt-text")
def copy_social_alt_text(post_id: int, db: Session = Depends(get_db)) -> dict:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    alt_text = (post.preview_payload or {}).get("alt_text") or ""
    return {"post_id": post.id, "copy_text": alt_text, "button_label": "Copy alt text"}


def set_social_status(db: Session, post_id: int, status: str) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    allowed = {"draft", "needs_review", "approved", "exported", "posted_manually", "rejected"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported social post status")
    preview = dict(post.preview_payload or {})
    post.status = status
    preview["status"] = status
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


def weekly_issue_payload(issue: WeeklyIssue) -> dict:
    return {
        "id": issue.id,
        "title": issue.title,
        "slug": issue.slug,
        "starts_on": issue.starts_on.isoformat(),
        "ends_on": issue.ends_on.isoformat(),
        "status": issue.status,
        "summary": issue.summary,
        "generated_at": issue.generated_at.isoformat() if issue.generated_at else None,
    }


def social_post_payload(post: SocialPost) -> dict:
    payload = post.preview_payload or {}
    hashtags = payload.get("hashtags", [])
    return {
        "id": post.id,
        "weekly_issue_id": post.weekly_issue_id,
        "event_id": post.event_id,
        "platform": post.platform,
        "template_name": post.template_name,
        "post_type": post.post_type,
        "caption": post.caption,
        "image_path": post.image_path,
        "image_url": post.image_url,
        "hashtags": hashtags,
        "alt_text": payload.get("alt_text"),
        "status": post.status,
        "publish_at": post.publish_at.isoformat() if post.publish_at else None,
        "planned_for": post.planned_for.isoformat() if post.planned_for else None,
        "exported_at": post.exported_at.isoformat() if post.exported_at else None,
        "posted_manually_at": (
            post.posted_manually_at.isoformat() if post.posted_manually_at else None
        ),
        "exports": payload.get("exports", {}),
        "copy_actions": {
            "caption": {
                "label": "Copy caption",
                "text": post.caption or "",
                "endpoint": f"/api/v1/admin/social/{post.id}/copy/caption",
            },
            "hashtags": {
                "label": "Copy hashtags",
                "text": " ".join(hashtags),
                "endpoint": f"/api/v1/admin/social/{post.id}/copy/hashtags",
            },
            "alt_text": {
                "label": "Copy alt text",
                "text": payload.get("alt_text") or "",
                "endpoint": f"/api/v1/admin/social/{post.id}/copy/alt-text",
            },
        },
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


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
        "source_url": event.source_url,
        "source_event_id": event.source_event_id,
        "image_url": event.image_url,
        "genre": event.genre,
        "price_min": str(event.price_min) if event.price_min is not None else None,
        "price_max": str(event.price_max) if event.price_max is not None else None,
        "status": event.status,
        "needs_review": event.needs_review,
        "confidence_score": event.confidence_score,
        "source_attribution": event.source_attribution,
        "editorial_note": event.editorial_note,
        "top_pick": bool(event.featured or metadata.get("top_pick")),
        "featured": event.featured,
        "instagram_suitable": event.instagram_suitable,
        "duplicate_of_event_id": event.duplicate_of_event_id,
        "duplicate_reason": event.duplicate_reason,
        "sponsored": bool(metadata.get("sponsored")),
    }
