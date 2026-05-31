from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.city import City
from app.models.event import Event
from app.models.social_post import SocialPost
from app.models.weekly_issue import WeeklyIssue
from app.services.venue_coverage import run_all_venue_checks


@dataclass(slots=True)
class WeeklyReport:
    city: str
    issue_slug: str
    events_selected: int
    post_created: bool
    coverage_report: dict


def generate_weekly_issue(db: Session, city_slug: str) -> WeeklyReport:
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise ValueError(f"City '{city_slug}' has not been seeded.")

    coverage_report = run_all_venue_checks(db, city_slug)

    starts_on, ends_on = next_friday_to_thursday()
    slug = slugify(f"{city.slug} gigs {starts_on.isoformat()}")
    issue = db.scalar(select(WeeklyIssue).where(WeeklyIssue.city_id == city.id, WeeklyIssue.slug == slug))
    if issue is None:
        issue = WeeklyIssue(
            city_id=city.id,
            title=f"Gigged {city.name}: {starts_on:%-d %b} to {ends_on:%-d %b}",
            slug=slug,
            starts_on=starts_on,
            ends_on=ends_on,
            status="draft",
        )
        db.add(issue)
        db.flush()

    start_dt = datetime.combine(starts_on, time.min)
    end_dt = datetime.combine(ends_on + timedelta(days=1), time.min)
    events = list(
        db.scalars(
            select(Event)
            .where(
                Event.city_id == city.id,
                Event.starts_at >= start_dt,
                Event.starts_at < end_dt,
            )
            .options(joinedload(Event.venue), joinedload(Event.artist))
            .order_by(Event.confidence_score.desc(), Event.starts_at.asc())
            .limit(8)
        )
    )

    issue.summary = build_issue_summary(events, coverage_report)
    issue.generated_at = datetime.utcnow()

    existing_post = db.scalar(
        select(SocialPost).where(
            SocialPost.city_id == city.id,
            SocialPost.weekly_issue_id == issue.id,
            SocialPost.template_name == "weekly_roundup",
        )
    )
    post_created = existing_post is None
    if existing_post is None:
        db.add(
            SocialPost(
                city_id=city.id,
                weekly_issue_id=issue.id,
                platform="instagram",
                template_name="weekly_roundup",
                caption=build_caption(city.name, starts_on, ends_on, events),
                image_prompt="Modern gig poster crossed with a useful city guide for Glasgow live music.",
                preview_payload={
                    "brand": "Gigged Glasgow",
                    "template": "weekly-roundup",
                    "available_templates": [
                        "weekly-roundup",
                        "carousel",
                        "tonight",
                        "under-15",
                        "hidden-gem",
                        "big-one",
                    ],
                    "title": "Glasgow gigs worth knowing",
                    "tagline": "Your weekly Glasgow gig radar.",
                    "palette": {
                        "ink": "#0e0e10",
                        "paper": "#f3efe4",
                        "acid": "#d6f84c",
                        "clyde": "#28b8a7",
                        "poster": "#ef4d2f",
                    },
                    "window": f"{starts_on.isoformat()} to {ends_on.isoformat()}",
                    "coverage_report": coverage_report["summary"],
                    "events": [
                        {
                            "title": event.title,
                            "venue": event.venue.name if event.venue else "Venue TBC",
                            "date": event.starts_at.date().isoformat(),
                        }
                        for event in events
                    ],
                },
                status="draft",
            )
        )
    db.commit()
    return WeeklyReport(
        city=city_slug,
        issue_slug=slug,
        events_selected=len(events),
        post_created=post_created,
        coverage_report=coverage_report["summary"],
    )


def next_friday_to_thursday(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    days_until_friday = (4 - today.weekday()) % 7
    starts_on = today + timedelta(days=days_until_friday)
    return starts_on, starts_on + timedelta(days=6)


def build_issue_summary(events: list[Event], coverage_report: dict | None = None) -> str:
    coverage_lines = []
    if coverage_report:
        summary = coverage_report.get("summary", coverage_report)
        coverage_lines = [
            "Coverage preflight:",
            str(summary.get("explanation", "Coverage report unavailable.")),
        ]
        coverage_lines.extend(f"- {item}" for item in summary.get("missing", [])[:4])
    if not events:
        event_lines = ["No ranked events available yet for this issue."]
    else:
        event_lines = [
            f"{event.starts_at:%a %-d %b}: {event.title} at {event.venue.name if event.venue else 'Venue TBC'}"
            for event in events
        ]
    return "\n".join([*coverage_lines, "", *event_lines]).strip()


def build_caption(city_name: str, starts_on: date, ends_on: date, events: list[Event]) -> str:
    lines = [f"{city_name} gig radar: {starts_on:%-d %b} to {ends_on:%-d %b}."]
    for event in events[:6]:
        venue = event.venue.name if event.venue else "Venue TBC"
        lines.append(f"- {event.starts_at:%a}: {event.title} at {venue}")
    lines.append("#GiggedGlasgow #GlasgowGigs #LiveMusic")
    return "\n".join(lines)
