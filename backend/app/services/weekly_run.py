from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.city import City
from app.models.event import Event
from app.models.social_post import SocialPost
from app.models.weekly_issue import WeeklyIssue
from app.services.deduplication import DedupeReport, dedupe_city
from app.services.ingestion import IngestionReport, ingest_city
from app.services.seed import seed_glasgow
from app.services.social_generation import (
    GeneratedPost,
    create_review_post,
    generate_alt_text,
    generate_caption,
    generate_hashtags,
)
from app.services.venue_coverage import run_all_venue_checks


@dataclass(slots=True)
class ScoredEvent:
    event: Event
    score: float
    breakdown: dict[str, float]
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WeeklyRunReport:
    city: str
    issue_id: int
    issue_slug: str
    ingest: dict[str, Any]
    venue_coverage: dict[str, Any]
    dedupe: dict[str, Any]
    candidates: list[dict[str, Any]]
    posts_created: list[dict[str, Any]]
    review_queue_count: int
    safe_to_publish: bool


def run_weekly_issue_workflow(db: Session, city_slug: str = "glasgow") -> WeeklyRunReport:
    if city_slug == "glasgow":
        seed_glasgow(db)
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise ValueError(f"City '{city_slug}' has not been seeded.")

    ingest_report = ingest_city(db, city_slug)
    coverage_report = run_all_venue_checks(db, city_slug, live_http=False)
    dedupe_report = dedupe_city(db, city_slug)

    scored_events = score_events_for_next_7_days(db, city)
    selected = select_recommended_events(scored_events, limit=10)
    issue = create_or_update_weekly_issue(db, city, coverage_report, selected)
    posts = generate_weekly_run_posts(db, city, issue, selected)
    review_queue_count = (
        db.scalar(
            select(func.count(SocialPost.id)).where(
                SocialPost.city_id == city.id,
                SocialPost.status.in_(["needs_review", "review"]),
            )
        )
        or 0
    )
    db.commit()

    return WeeklyRunReport(
        city=city_slug,
        issue_id=issue.id,
        issue_slug=issue.slug,
        ingest=ingestion_payload(ingest_report),
        venue_coverage=coverage_report["pre_publish_report"],
        dedupe=dedupe_payload(dedupe_report),
        candidates=[scored_event_payload(item) for item in selected],
        posts_created=[post_payload(post) for post in posts],
        review_queue_count=review_queue_count,
        safe_to_publish=bool(
            coverage_report.get("pre_publish_report", {}).get("safe_to_publish", False)
        ),
    )


def score_events_for_next_7_days(db: Session, city: City) -> list[ScoredEvent]:
    now = datetime.utcnow()
    end = now + timedelta(days=7)
    events = list(
        db.scalars(
            select(Event)
            .where(
                Event.city_id == city.id,
                Event.starts_at >= now,
                Event.starts_at < end,
                Event.status == "scheduled",
            )
            .options(
                joinedload(Event.artist),
                joinedload(Event.venue),
                joinedload(Event.source),
            )
            .order_by(Event.starts_at.asc())
        )
    )

    scored = [score_event(event, now) for event in events]
    genres_seen: set[str] = set()
    for item in sorted(scored, key=lambda candidate: candidate.score, reverse=True):
        genre = (item.event.genre or "").lower()
        if genre and genre not in genres_seen:
            item.breakdown["genre_variety"] = 0.08
            item.score = round(min(1.0, item.score + 0.08), 3)
            item.reasons.append(f"Adds {item.event.genre} variety")
            genres_seen.add(genre)
        else:
            item.breakdown["genre_variety"] = 0.0
        persist_event_score(item)
    db.flush()
    return sorted(scored, key=lambda candidate: candidate.score, reverse=True)


def score_event(event: Event, now: datetime) -> ScoredEvent:
    breakdown = {
        "venue_importance": venue_importance_score(event),
        "artist_popularity": artist_popularity_score(event),
        "ticket_price": ticket_price_score(event.price_min),
        "date_proximity": date_proximity_score(event, now),
        "source_confidence": min(float(event.confidence_score or 0), 1.0) * 0.18,
        "unique_interest": unique_interest_score(event),
        "social_potential": social_potential_score(event),
    }
    score = round(min(sum(breakdown.values()), 1.0), 3)
    reasons = score_reasons(event, breakdown)
    return ScoredEvent(event=event, score=score, breakdown=breakdown, reasons=reasons)


def venue_importance_score(event: Event) -> float:
    venue = event.venue
    if venue is None:
        return 0.04
    score = 0.06
    if venue.is_whitelisted:
        score += 0.05
    if venue.capacity:
        if venue.capacity >= 2000:
            score += 0.08
        elif venue.capacity >= 500:
            score += 0.06
        else:
            score += 0.04
    return min(score, 0.18)


def artist_popularity_score(event: Event) -> float:
    artist = event.artist
    if artist is None:
        return 0.03
    score = 0.04
    if artist.instagram_handle:
        score += 0.04
    if artist.website_url:
        score += 0.03
    return min(score, 0.12)


def ticket_price_score(price: Decimal | None) -> float:
    if price is None:
        return 0.06
    value = float(price)
    if value <= 10:
        return 0.12
    if value <= 15:
        return 0.1
    if value <= 25:
        return 0.07
    return 0.04


def date_proximity_score(event: Event, now: datetime) -> float:
    starts_at = event.starts_at
    if starts_at.tzinfo is not None and now.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=None)
    days_until = max((starts_at - now).days, 0)
    return max(0.03, 0.13 - (days_until * 0.015))


def unique_interest_score(event: Event) -> float:
    score = 0.04
    title = event.title.lower()
    if event.genre and event.genre.lower() not in {"pop", "rock"}:
        score += 0.04
    if any(token in title for token in ["debut", "launch", "festival", "special", "anniversary"]):
        score += 0.04
    if event.venue and event.venue.capacity and event.venue.capacity <= 300:
        score += 0.03
    return min(score, 0.13)


def social_potential_score(event: Event) -> float:
    score = 0.04
    if event.image_url:
        score += 0.05
    if event.ticket_url:
        score += 0.03
    if event.artist and event.artist.instagram_handle:
        score += 0.03
    if 8 <= len(event.title) <= 90:
        score += 0.02
    return min(score, 0.13)


def score_reasons(event: Event, breakdown: dict[str, float]) -> list[str]:
    reasons = []
    if breakdown["venue_importance"] >= 0.14 and event.venue:
        reasons.append(f"Strong venue signal: {event.venue.name}")
    if breakdown["ticket_price"] >= 0.1:
        reasons.append("Affordable ticket")
    if breakdown["date_proximity"] >= 0.1:
        reasons.append("Happening soon")
    if breakdown["source_confidence"] >= 0.14:
        reasons.append("High source confidence")
    if breakdown["unique_interest"] >= 0.08:
        reasons.append("Distinctive or smaller-room pick")
    if breakdown["social_potential"] >= 0.09:
        reasons.append("Good social content potential")
    return reasons


def persist_event_score(item: ScoredEvent) -> None:
    metadata = dict(item.event.raw_payload or {})
    metadata["weekly_run_score"] = {
        "score": item.score,
        "breakdown": item.breakdown,
        "reasons": item.reasons,
        "scored_at": datetime.utcnow().isoformat(),
    }
    item.event.raw_payload = metadata


def select_recommended_events(scored_events: list[ScoredEvent], limit: int) -> list[ScoredEvent]:
    selected: list[ScoredEvent] = []
    used_genres: set[str] = set()
    for item in scored_events:
        genre = (item.event.genre or "").lower()
        if genre and genre in used_genres and len(selected) < min(4, limit):
            continue
        selected.append(item)
        if genre:
            used_genres.add(genre)
        if len(selected) == limit:
            return selected
    for item in scored_events:
        if item not in selected:
            selected.append(item)
        if len(selected) == limit:
            break
    return selected


def create_or_update_weekly_issue(
    db: Session,
    city: City,
    coverage_report: dict[str, Any],
    selected: list[ScoredEvent],
) -> WeeklyIssue:
    now = datetime.utcnow()
    starts_on = now.date()
    ends_on = (now + timedelta(days=7)).date()
    slug = slugify(f"{city.slug} weekly run {starts_on.isoformat()}")
    issue = db.scalar(select(WeeklyIssue).where(WeeklyIssue.city_id == city.id, WeeklyIssue.slug == slug))
    if issue is None:
        issue = WeeklyIssue(
            city_id=city.id,
            title=f"Weekly Run: {city.name} gigs from {starts_on:%-d %b}",
            slug=slug,
            starts_on=starts_on,
            ends_on=ends_on,
            status="draft",
        )
        db.add(issue)
        db.flush()

    issue.summary = build_weekly_run_summary(coverage_report, selected)
    issue.generated_at = now
    return issue


def generate_weekly_run_posts(
    db: Session,
    city: City,
    issue: WeeklyIssue,
    selected: list[ScoredEvent],
) -> list[SocialPost]:
    events = [item.event for item in selected]
    generated_posts = [
        generated_post("weekly_top_10", "Weekly Top 10 Glasgow Gigs", "The strongest scored gigs for the next seven days.", events[:10], city.name),
        generated_post("weekend_picks", "Weekend Picks", "Friday-to-Sunday gigs worth saving.", weekend_events(events)[:6], city.name),
        generated_post("under_15", "Cheap Gigs Under £15", "Low-cost Glasgow gigs that still feel worth the night out.", cheap_events(events)[:6], city.name),
        generated_post("hidden_gem", "Hidden Gem", "A smaller-room pick with enough signal to deserve attention.", hidden_gem_events(events)[:1], city.name),
    ]

    posts = []
    for generated in generated_posts:
        if not generated.events:
            continue
        post = create_review_post(db, city, generated, weekly_issue_id=issue.id)
        payload = dict(post.preview_payload or {})
        payload["weekly_run"] = {
            "issue_id": issue.id,
            "issue_slug": issue.slug,
            "auto_publish": False,
            "requires_approval": True,
        }
        post.preview_payload = payload
        posts.append(post)
    return posts


def generated_post(
    post_format,
    title: str,
    description: str,
    events: list[Event],
    city_name: str,
) -> GeneratedPost:
    return GeneratedPost(
        format=post_format,
        title=title,
        description=description,
        caption=generate_caption(title, description, events, city_name),
        hashtags=generate_hashtags(post_format, events, city_name),
        alt_text=generate_alt_text(title, events),
        events=events,
        venue=events[0].venue if events else None,
    )


def weekend_events(events: list[Event]) -> list[Event]:
    return [event for event in events if event.starts_at.weekday() in {4, 5, 6}] or events[:4]


def cheap_events(events: list[Event]) -> list[Event]:
    return [
        event for event in events if event.price_min is not None and float(event.price_min) <= 15
    ] or events[:3]


def hidden_gem_events(events: list[Event]) -> list[Event]:
    return sorted(
        events,
        key=lambda event: (
            bool(event.venue and event.venue.capacity and event.venue.capacity <= 300),
            float((event.raw_payload or {}).get("weekly_run_score", {}).get("score", 0)),
        ),
        reverse=True,
    )


def build_weekly_run_summary(coverage_report: dict[str, Any], selected: list[ScoredEvent]) -> str:
    pre_publish = coverage_report.get("pre_publish_report", {})
    lines = [
        "Weekly Run generated review drafts only.",
        f"Safe to publish: {pre_publish.get('safe_to_publish', False)}",
        f"Venues checked: {pre_publish.get('venues_checked', 0)}",
        "",
        "Candidate events:",
    ]
    lines.extend(
        f"- {item.score:.2f}: {item.event.title} at {item.event.venue.name if item.event.venue else 'Venue TBC'}"
        for item in selected
    )
    return "\n".join(lines)


def ingestion_payload(report: IngestionReport) -> dict[str, Any]:
    return {
        "events_found": report.fetched,
        "events_created": report.created,
        "events_updated": report.updated,
        "duplicates_skipped": report.skipped,
        "failures": report.failures,
        "warnings": report.warnings,
        "source_logs": report.source_logs,
    }


def dedupe_payload(report: DedupeReport) -> dict[str, Any]:
    return {
        "reviewed": report.reviewed,
        "merged": report.merged,
        "marked_for_review": report.marked_for_review,
        "updated_fingerprints": report.updated_fingerprints,
    }


def scored_event_payload(item: ScoredEvent) -> dict[str, Any]:
    event = item.event
    return {
        "event_id": event.id,
        "title": event.title,
        "artist": event.artist.name if event.artist else event.title,
        "venue": event.venue.name if event.venue else "Venue TBC",
        "starts_at": event.starts_at.isoformat(),
        "price_min": str(event.price_min) if event.price_min is not None else None,
        "genre": event.genre,
        "score": item.score,
        "score_breakdown": item.breakdown,
        "reasons": item.reasons,
        "needs_review": event.needs_review,
        "source_attribution": event.source_attribution,
    }


def post_payload(post: SocialPost) -> dict[str, Any]:
    exports = (post.preview_payload or {}).get("exports", {})
    return {
        "post_id": post.id,
        "template_name": post.template_name,
        "status": post.status,
        "planned_for": post.planned_for.isoformat() if post.planned_for else None,
        "caption": post.caption,
        "exports": exports,
    }
