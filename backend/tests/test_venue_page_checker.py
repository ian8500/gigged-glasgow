from __future__ import annotations

import json
import importlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.city import City
from app.models.event import Event
from app.models.venue import Venue
from app.services.venue_page_checker import FetchResponse, check_venue_page
from app.sources.feed import parse_ical_events


for model_module in [
    "app.models.app_setting",
    "app.models.artist",
    "app.models.city_brand",
    "app.models.city",
    "app.models.event",
    "app.models.ingestion_log",
    "app.models.promoter_submission",
    "app.models.source",
    "app.models.source_feed",
    "app.models.source_health",
    "app.models.social_post",
    "app.models.venue",
    "app.models.venue_check_log",
    "app.models.venue_coverage",
    "app.models.weekly_issue",
]:
    importlib.import_module(model_module)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(City(slug="glasgow", name="Glasgow"))
        db.commit()
        yield db
    finally:
        db.close()


def add_venue(db_session, **values) -> Venue:
    city_record = db_session.scalar(select(City).where(City.slug == "glasgow"))
    venue = Venue(
        city_id=city_record.id,
        name=values.pop("name", "Test Venue"),
        slug=values.pop("slug", "test-venue"),
        is_whitelisted=True,
        **values,
    )
    db_session.add(venue)
    db_session.commit()
    return venue


def event_html(payload: dict | list[dict]) -> str:
    return (
        '<html><head><script type="application/ld+json">'
        f"{json.dumps(payload)}"
        "</script></head><body>Events</body></html>"
    )


def test_robots_disallowed_case(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        official_events_url="https://venue.example/events",
        source_mode="structured_data",
    )
    monkeypatch.setattr(
        "app.services.venue_page_checker.robots_allows",
        lambda url: (False, "robots.txt disallows automated checks for this configured URL."),
    )

    def fail_fetch(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("fetch should not run when robots disallows the URL")

    monkeypatch.setattr("app.services.venue_page_checker.fetch_public_url", fail_fetch)

    report = check_venue_page(db_session, venue.id)
    db_session.refresh(venue)

    assert report.events_found == 0
    assert report.coverage_status == "unsupported"
    assert venue.robots_allowed is False
    assert "html" not in report.diagnostic_summary


def test_json_ld_event_extraction_creates_review_event(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        official_events_url="https://venue.example/events",
        source_mode="structured_data",
    )
    payload = {
        "@type": "Event",
        "@id": "https://venue.example/events/sample",
        "name": "Sample JSON-LD Gig",
        "startDate": "2026-06-05T19:30:00+01:00",
        "location": {"name": "Test Venue"},
        "offers": {"url": "https://venue.example/tickets", "price": "12.50", "priceCurrency": "GBP"},
        "image": "https://venue.example/image.jpg",
    }
    monkeypatch.setattr("app.services.venue_page_checker.robots_allows", lambda url: (True, "allowed"))
    monkeypatch.setattr(
        "app.services.venue_page_checker.fetch_public_url",
        lambda url, accept="*/*": FetchResponse(
            ok=True,
            url=url,
            status_code=200,
            content_type="text/html",
            body=event_html(payload),
        ),
    )

    report = check_venue_page(db_session, venue.id)
    stored_event = db_session.scalar(select(Event).where(Event.title == "Sample JSON-LD Gig"))

    assert report.events_created == 1
    assert stored_event is not None
    assert stored_event.needs_review is True
    assert stored_event.ticket_url == "https://venue.example/tickets"
    assert str(stored_event.price_min) == "12.50"


def test_rss_feed_extraction_creates_review_event(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        feed_url="https://venue.example/feed.xml",
        source_mode="feed",
    )
    raw = """<?xml version="1.0"?>
    <rss><channel><item>
      <title>Sample RSS Gig</title>
      <link>https://venue.example/rss-gig</link>
      <pubDate>Fri, 05 Jun 2026 19:30:00 GMT</pubDate>
      <description>Venue: Test Venue</description>
    </item></channel></rss>"""
    monkeypatch.setattr("app.services.venue_page_checker.robots_allows", lambda url: (True, "allowed"))
    monkeypatch.setattr(
        "app.services.venue_page_checker.fetch_public_url",
        lambda url, accept="*/*": FetchResponse(
            ok=True,
            url=url,
            status_code=200,
            content_type="application/rss+xml",
            body=raw,
        ),
    )

    report = check_venue_page(db_session, venue.id)

    assert report.coverage_type == "feed"
    assert report.events_created == 1
    assert db_session.scalar(select(Event).where(Event.title == "Sample RSS Gig")).needs_review is True


def test_ical_extraction() -> None:
    raw = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-1
SUMMARY:Sample iCal Gig
DTSTART:20260605T193000Z
DTEND:20260605T220000Z
LOCATION:Test Venue
URL:https://venue.example/ical-gig
END:VEVENT
END:VCALENDAR"""

    events = parse_ical_events(raw, "Official venue feed", "https://venue.example/events.ics")

    assert len(events) == 1
    assert events[0].title == "Sample iCal Gig"
    assert events[0].starts_at == datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc)
    assert events[0].source_event_id == "event-1"


def test_broken_venue_page(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        official_events_url="https://venue.example/missing",
        source_mode="structured_data",
    )
    monkeypatch.setattr("app.services.venue_page_checker.robots_allows", lambda url: (True, "allowed"))
    monkeypatch.setattr(
        "app.services.venue_page_checker.fetch_public_url",
        lambda url, accept="*/*": FetchResponse(
            ok=False,
            url=url,
            status_code=404,
            error="Configured source returned HTTP 404.",
        ),
    )

    report = check_venue_page(db_session, venue.id)
    db_session.refresh(venue)

    assert report.coverage_status == "broken"
    assert report.structure_changed is True
    assert venue.last_error == "Configured source returned HTTP 404."


def test_duplicate_event_handling(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        official_events_url="https://venue.example/events",
        source_mode="structured_data",
    )
    item = {
        "@type": "Event",
        "@id": "https://venue.example/events/dupe",
        "name": "Duplicate Gig",
        "startDate": "2026-06-05T19:30:00Z",
        "location": {"name": "Test Venue"},
    }
    monkeypatch.setattr("app.services.venue_page_checker.robots_allows", lambda url: (True, "allowed"))
    monkeypatch.setattr(
        "app.services.venue_page_checker.fetch_public_url",
        lambda url, accept="*/*": FetchResponse(
            ok=True,
            url=url,
            status_code=200,
            content_type="text/html",
            body=event_html([item, item]),
        ),
    )

    report = check_venue_page(db_session, venue.id)

    assert report.events_found == 1
    assert db_session.scalars(select(Event).where(Event.title == "Duplicate Gig")).all().__len__() == 1


def test_low_confidence_review_queue(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        official_events_url="https://venue.example/events",
        source_mode="structured_data",
    )
    payload = {
        "@type": "Event",
        "name": "Sparse Venue Listing",
        "startDate": "2026-06-05T19:30:00Z",
    }
    monkeypatch.setattr("app.services.venue_page_checker.robots_allows", lambda url: (True, "allowed"))
    monkeypatch.setattr(
        "app.services.venue_page_checker.fetch_public_url",
        lambda url, accept="*/*": FetchResponse(
            ok=True,
            url=url,
            status_code=200,
            content_type="text/html",
            body=event_html(payload),
        ),
    )

    check_venue_page(db_session, venue.id)
    stored_event = db_session.scalar(select(Event).where(Event.title == "Sparse Venue Listing"))

    assert stored_event.needs_review is True
    assert stored_event.confidence_score < 0.7
    assert stored_event.raw_payload["low_confidence"] is True
