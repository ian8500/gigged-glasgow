from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings
from app.db.session import Base
from app.main import app
from app.models.city import City
from app.models.event import Event
from app.models.extracted_event_candidate import ExtractedEventCandidate
from app.models.venue import Venue
from app.services.venue_scraper import (
    FetchResponse,
    CandidateData,
    convert_candidate_to_event,
    dedupe_candidate,
    extract_ical_events,
    extract_json_ld_events,
    extract_rss_or_atom_events,
    scrape_venue,
)


for model_module in [
    "app.models.app_setting",
    "app.models.artist",
    "app.models.city_brand",
    "app.models.city",
    "app.models.event",
    "app.models.extracted_event_candidate",
    "app.models.ingestion_log",
    "app.models.promoter_submission",
    "app.models.scrape_run",
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


def test_json_ld_extraction() -> None:
    payload = {
        "@type": "Event",
        "name": "Schema Gig",
        "startDate": "2026-06-05T19:30:00+01:00",
        "endDate": "2026-06-05T22:00:00+01:00",
        "location": {"name": "Test Venue", "address": "Glasgow"},
        "offers": {"url": "https://venue.example/tickets", "price": "12.50"},
        "image": "https://venue.example/poster.jpg",
        "description": "A safe structured data event.",
    }
    html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'

    candidates = extract_json_ld_events(html, "https://venue.example/events")

    assert len(candidates) == 1
    assert candidates[0].title == "Schema Gig"
    assert candidates[0].ticket_url == "https://venue.example/tickets"
    assert candidates[0].price_text == "12.50"
    assert candidates[0].image_url == "https://venue.example/poster.jpg"


def test_rss_extraction(monkeypatch) -> None:
    raw = """<?xml version="1.0"?>
    <rss><channel><item>
      <title>RSS Gig</title>
      <link>https://venue.example/rss-gig</link>
      <pubDate>Fri, 05 Jun 2026 19:30:00 GMT</pubDate>
    </item></channel></rss>"""
    monkeypatch.setattr(
        "app.services.venue_scraper.fetch_public_page",
        lambda url: FetchResponse(ok=True, url=url, status_code=200, body=raw),
    )

    candidates = extract_rss_or_atom_events("https://venue.example/feed.xml")

    assert len(candidates) == 1
    assert candidates[0].title == "RSS Gig"
    assert candidates[0].starts_at == datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc)


def test_ical_extraction(monkeypatch) -> None:
    raw = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-1
SUMMARY:iCal Gig
DTSTART:20260605T193000Z
URL:https://venue.example/ical-gig
END:VEVENT
END:VCALENDAR"""
    monkeypatch.setattr(
        "app.services.venue_scraper.fetch_public_page",
        lambda url: FetchResponse(ok=True, url=url, status_code=200, body=raw),
    )

    candidates = extract_ical_events("https://venue.example/events.ics")

    assert len(candidates) == 1
    assert candidates[0].title == "iCal Gig"
    assert candidates[0].ticket_url == "https://venue.example/ical-gig"


def test_robots_disallowed(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        event_listings_url="https://venue.example/events",
        source_mode="structured_data",
    )
    monkeypatch.setattr(
        "app.services.venue_scraper.robots_allowed",
        lambda url: (False, "robots.txt disallows automated checks for this configured URL."),
    )

    result = scrape_venue(venue.id, db=db_session)
    db_session.refresh(venue)

    assert result.status == "robots_blocked"
    assert venue.scraper_status == "robots_blocked"
    assert db_session.scalars(select(ExtractedEventCandidate)).all() == []


def test_broken_venue_page(monkeypatch, db_session) -> None:
    venue = add_venue(
        db_session,
        event_listings_url="https://venue.example/missing",
        source_mode="structured_data",
    )
    monkeypatch.setattr("app.services.venue_scraper.robots_allowed", lambda url: (True, "allowed"))
    monkeypatch.setattr(
        "app.services.venue_scraper.fetch_public_page",
        lambda url: FetchResponse(ok=False, url=url, status_code=404, error="Configured source returned HTTP 404."),
    )

    result = scrape_venue(venue.id, db=db_session)
    db_session.refresh(venue)

    assert result.status == "broken"
    assert venue.scraper_status == "broken"
    assert "404" in venue.scraper_notes


def test_candidate_dedupe(db_session) -> None:
    venue = add_venue(db_session)
    city_record = db_session.scalar(select(City).where(City.slug == "glasgow"))
    event = Event(
        city_id=city_record.id,
        venue_id=venue.id,
        title="Duplicate Gig",
        slug="duplicate-gig",
        starts_at=datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc),
        ticket_url="https://venue.example/tickets",
        source_url="https://venue.example/events/dupe",
        source_attribution="test",
    )
    db_session.add(event)
    db_session.commit()

    duplicate, existing_id = dedupe_candidate(
        CandidateData(
            venue_id=venue.id,
            city_slug="glasgow",
            source_url="https://venue.example/events/dupe",
            title="Duplicate Gig",
            starts_at=datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc),
        ),
        db_session,
    )

    assert duplicate is True
    assert existing_id == event.id


def test_candidate_approve_reject_api(db_session, monkeypatch) -> None:
    # Route-level auth and status transitions are covered against the app DB.
    with TestClient(app) as client:
        headers = {"X-Admin-Token": settings.admin_api_key}
        client.post("/api/v1/admin/seed/glasgow", headers=headers)
        response = client.get("/api/v1/venues?city=glasgow")
        venue_id = response.json()[0]["id"]

        monkeypatch.setattr("app.services.venue_scraper.robots_allowed", lambda url: (True, "allowed"))
        monkeypatch.setattr(
            "app.services.venue_scraper.fetch_public_page",
            lambda url: FetchResponse(
                ok=True,
                url=url,
                status_code=200,
                body='<script type="application/ld+json">{"@type":"Event","name":"API Candidate Route","startDate":"2026-06-06T19:30:00Z"}</script>',
            ),
        )
        client.patch(
            f"/api/v1/venues/{venue_id}",
            headers=headers,
            json={"event_listings_url": "https://venue.example/events", "source_mode": "structured_data"},
        )
        run = client.post(f"/api/v1/admin/scrape/venues/{venue_id}", headers=headers)
        assert run.status_code == 200
        candidates = client.get("/api/v1/admin/scrape/candidates?city=glasgow", headers=headers).json()
        candidate_id = next(item["id"] for item in candidates if item["title"] == "API Candidate Route")

        approved = client.post(f"/api/v1/admin/scrape/candidates/{candidate_id}/approve", headers=headers)
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        rejected = client.post(f"/api/v1/admin/scrape/candidates/{candidate_id}/reject", headers=headers)
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"


def test_convert_candidate_to_event(db_session) -> None:
    venue = add_venue(db_session)
    candidate = ExtractedEventCandidate(
        venue_id=venue.id,
        city_slug="glasgow",
        source_url="https://venue.example/events/schema",
        source_type="structured_data",
        raw_title="Convert Me",
        title="Convert Me",
        starts_at=datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc),
        ticket_url="https://venue.example/tickets",
        confidence_score=0.82,
        status="needs_review",
        raw_payload={"diagnostic": "test"},
    )
    db_session.add(candidate)
    db_session.commit()

    event = convert_candidate_to_event(db_session, candidate.id)

    assert event.title == "Convert Me"
    assert event.status == "scheduled"
    assert event.needs_review is False
    assert event.source_url == "https://venue.example/events/schema"
