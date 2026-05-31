from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

from app.cities.glasgow import GLASGOW_CONFIG
from app.services.normalization import fingerprint_parts
from app.core.settings import settings
from app.services.social_generation import export_carousel_pngs, export_square_png
from app.services.venue_coverage import build_pre_publish_report
from app.services.weekly import next_friday_to_thursday
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter


def test_fingerprint_uses_city_title_venue_and_date() -> None:
    fingerprint = fingerprint_parts(
        city_slug="glasgow",
        title="Sample Artist at King Tut's",
        venue_name="King Tut's Wah Wah Hut",
        starts_at=datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc),
    )

    assert fingerprint == "glasgow-sample-artist-at-king-tuts-king-tuts-wah-wah-hut-2026-06-05"


def test_weekly_window_runs_friday_to_thursday() -> None:
    starts_on, ends_on = next_friday_to_thursday(date(2026, 5, 31))

    assert starts_on == date(2026, 6, 5)
    assert ends_on == date(2026, 6, 11)


def test_ticketmaster_adapter_uses_glasgow_music_query(monkeypatch) -> None:
    seen_urls: list[str] = []
    monkeypatch.setattr(settings, "ticketmaster_api_key", "test-key")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "page": {"totalPages": 1},
                    "_embedded": {
                        "events": [
                            {
                                "id": "tm-1",
                                "name": "Sample Glasgow Gig",
                                "url": "https://ticketmaster.example/event/tm-1",
                                "dates": {
                                    "start": {"dateTime": "2026-06-05T19:30:00Z"},
                                    "status": {"code": "onsale"},
                                },
                                "_embedded": {
                                    "venues": [{"name": "King Tut's Wah Wah Hut"}],
                                    "attractions": [{"name": "Sample Artist"}],
                                },
                                "priceRanges": [{"min": 12.5, "max": 18, "currency": "GBP"}],
                                "images": [{"url": "https://example.test/image.jpg", "width": 1200}],
                                "classifications": [{"genre": {"name": "Rock"}}],
                            }
                        ]
                    },
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr("app.sources.ticketmaster.urlopen", fake_urlopen)

    result = TicketmasterDiscoveryAdapter().fetch(
        GLASGOW_CONFIG,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )

    query = parse_qs(urlparse(seen_urls[0]).query)
    assert query["city"] == ["Glasgow"]
    assert query["countryCode"] == ["GB"]
    assert query["classificationName"] == ["music"]
    assert query["startDateTime"] == ["2026-06-01T00:00:00Z"]
    assert query["endDateTime"] == ["2026-07-01T00:00:00Z"]
    assert result.events[0].source_event_id == "tm-1"
    assert result.events[0].source_url == "https://ticketmaster.example/event/tm-1"
    assert result.events[0].venue_name == "King Tut's Wah Wah Hut"


def test_glasgow_venue_coverage_seed_contains_requested_venues() -> None:
    seed_path = Path("seeds/glasgow_venue_coverage.json")
    venues = json.loads(seed_path.read_text(encoding="utf-8"))
    names = {venue["name"] for venue in venues}

    assert len(venues) == 31
    assert {
        "Barrowland Ballroom",
        "King Tut's Wah Wah Hut",
        "SWG3",
        "OVO Hydro",
        "SEC Armadillo",
        "O2 Academy Glasgow",
        "Glasgow Royal Concert Hall",
        "Saint Luke's",
        "Òran Mór",
        "The Garage",
        "G2",
        "Classic Grand",
        "Broadcast",
        "The Hug and Pint",
        "Stereo",
        "Mono",
        "Nice N Sleazy",
        "McChuills",
        "Slay",
        "Room 2",
        "The Old Hairdressers",
        "Drygate",
        "The Glad Cafe",
        "The Rum Shack",
        "Ivory Blacks",
        "Audio Glasgow",
        "Cathouse",
        "Platform",
        "Kelvingrove Bandstand",
        "Bellahouston Park",
        "Hampden Park",
    } == names


def test_pre_publish_report_requires_healthy_coverage() -> None:
    report = build_pre_publish_report(
        {
            "sources_checked": 31,
            "sources_working": 20,
            "sources_failed": 1,
            "venues_not_checked_in_30_days": 0,
            "coverage_percentage": 80,
            "venues_may_be_missing_events": [],
        },
        [],
    )

    assert report["safe_to_publish"] is False
    assert report["sources_failed"] == 1


def test_instagram_exports_square_and_carousel_dimensions() -> None:
    payload = {
        "post_id": 999999,
        "format": "dimension_test",
        "title": "Dimension Test",
        "description": "Generated asset dimension test.",
        "caption": "Caption",
        "hashtags": ["#GiggedGlasgow"],
        "alt_text": "Alt text",
        "events": [
            {
                "date": "2026-06-05",
                "artist": "Sample Artist",
                "venue": "Sample Venue",
                "ticket_price": "£10.00",
            }
        ],
        "carousel_slides": [
            {
                "slide": 1,
                "title": "Dimension Test",
                "description": "Generated asset dimension test.",
                "events": [
                    {
                        "date": "2026-06-05",
                        "artist": "Sample Artist",
                        "venue": "Sample Venue",
                        "ticket_price": "£10.00",
                    }
                ],
            }
        ],
    }

    square_path = export_square_png(payload)
    carousel_path = export_carousel_pngs(payload)[0]

    with Image.open(square_path) as square:
        assert square.size == (1080, 1080)
    with Image.open(carousel_path) as carousel:
        assert carousel.size == (1080, 1350)
