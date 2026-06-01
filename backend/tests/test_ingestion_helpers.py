from __future__ import annotations

import json
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from PIL import Image

from app.cities.glasgow import GLASGOW_CONFIG
from app.services.normalization import fingerprint_parts
from app.core.settings import settings
from app.services.social_generation import export_carousel_pngs, export_square_png
from app.services.venue_coverage import build_pre_publish_report
from app.services.weekly import next_friday_to_thursday
from app.sources.bandsintown import BandsintownAdapter
from app.sources.eventbrite import EventbriteAdapter
from app.sources.feed import parse_ical_events, parse_rss_events
from app.sources.songkick import SongkickAdapter
from app.sources.structured_data import extract_json_ld_events
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


def test_eventbrite_adapter_uses_official_search_and_normalises(monkeypatch) -> None:
    seen_requests = []
    monkeypatch.setattr(settings, "eventbrite_api_key", "eventbrite-test-token")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "pagination": {"has_more_items": False},
                    "events": [
                        {
                            "id": "eb-1",
                            "name": {"text": "Sample Eventbrite Gig"},
                            "url": "https://eventbrite.example/e/eb-1",
                            "start": {"utc": "2026-06-05T19:30:00Z"},
                            "end": {"utc": "2026-06-05T22:30:00Z"},
                            "status": "live",
                            "currency": "GBP",
                            "venue": {"name": "Stereo"},
                            "organizer": {"name": "Sample Promoter"},
                            "category": {"name": "Music"},
                            "ticket_availability": {
                                "minimum_ticket_price": {"currency": "GBP", "major_value": "12.50"},
                                "maximum_ticket_price": {"currency": "GBP", "major_value": "18.00"},
                            },
                            "logo": {"original": {"url": "https://example.test/eventbrite.jpg"}},
                        }
                    ],
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        seen_requests.append(request)
        return FakeResponse()

    monkeypatch.setattr("app.sources.eventbrite.urlopen", fake_urlopen)

    result = EventbriteAdapter().fetch(
        GLASGOW_CONFIG,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )

    request = seen_requests[0]
    query = parse_qs(urlparse(request.full_url).query)
    assert request.full_url.startswith("https://www.eventbriteapi.com/v3/events/search/")
    assert request.get_header("Authorization") == "Bearer eventbrite-test-token"
    assert query["location.address"] == ["Glasgow, Scotland, United Kingdom"]
    assert query["location.within"] == ["24km"]
    assert query["categories"] == ["103"]
    assert query["start_date.range_start"] == ["2026-06-01T00:00:00Z"]
    assert query["start_date.range_end"] == ["2026-07-01T00:00:00Z"]
    assert result.events[0].source_event_id == "eb-1"
    assert result.events[0].source_attribution == "Eventbrite API"
    assert result.events[0].venue_name == "Stereo"
    assert result.events[0].price_min is not None


def test_eventbrite_profile_test_uses_users_me_without_token_query(monkeypatch) -> None:
    seen_requests = []
    monkeypatch.setattr(settings, "eventbrite_api_key", "eventbrite-test-token")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"id": "user-1", "emails": [{"email": "owner@example.test"}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        seen_requests.append(request)
        return FakeResponse()

    monkeypatch.setattr("app.sources.eventbrite.urlopen", fake_urlopen)

    ok, message = EventbriteAdapter().test_connection()

    assert ok is True
    assert "owner@example.test" in message
    assert seen_requests[0].full_url == "https://www.eventbriteapi.com/v3/users/me/"
    assert "eventbrite-test-token" not in seen_requests[0].full_url
    assert seen_requests[0].get_header("Authorization") == "Bearer eventbrite-test-token"


def test_eventbrite_discovery_unavailable_is_reported_clearly(monkeypatch) -> None:
    seen_urls: list[str] = []
    monkeypatch.setattr(settings, "eventbrite_api_key", "eventbrite-test-token")

    class FakeProfileResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"id": "user-1"}).encode("utf-8")

    def fake_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        if request.full_url.endswith("/users/me/"):
            return FakeProfileResponse()
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=BytesIO(json.dumps({"error_description": "Forbidden"}).encode("utf-8")),
        )

    monkeypatch.setattr("app.sources.eventbrite.urlopen", fake_urlopen)

    result = EventbriteAdapter().fetch(
        GLASGOW_CONFIG,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )

    assert result.events == []
    assert result.failures == []
    assert "public discovery is unavailable" in result.warnings[0]
    assert any(url.endswith("/users/me/") for url in seen_urls)


def test_bandsintown_artist_seed_filters_to_glasgow(monkeypatch) -> None:
    monkeypatch.setattr(settings, "bandsintown_app_id", "bit-key")
    monkeypatch.setattr(settings, "bandsintown_artist_seed_list", "Mogwai")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                [
                    {
                        "id": "bit-1",
                        "title": "Mogwai",
                        "datetime": "2026-06-05T19:30:00",
                        "url": "https://bandsintown.example/e/1",
                        "lineup": ["Mogwai"],
                        "venue": {"name": "Barrowland Ballroom", "city": "Glasgow", "postal_code": "G4 0TT"},
                    }
                ]
            ).encode("utf-8")

    monkeypatch.setattr("app.sources.bandsintown.urlopen", lambda request, timeout: FakeResponse())

    result = BandsintownAdapter().fetch(
        GLASGOW_CONFIG,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )

    assert result.events[0].source_event_id == "bit-1"
    assert result.events[0].source_attribution == "Bandsintown API"
    assert result.events[0].venue_name == "Barrowland Ballroom"


def test_songkick_partner_mode_normalises_metro_events(monkeypatch) -> None:
    monkeypatch.setattr(settings, "songkick_api_key", "sk-key")
    monkeypatch.setattr(settings, "songkick_partner_mode", True)
    monkeypatch.setattr(settings, "songkick_metro_area_id", "24475")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "resultsPage": {
                        "status": "ok",
                        "perPage": 50,
                        "totalEntries": 1,
                        "results": {
                            "event": [
                                {
                                    "id": 1,
                                    "displayName": "Sample Songkick Gig",
                                    "uri": "https://songkick.example/e/1",
                                    "start": {"datetime": "2026-06-05T19:30:00+0000"},
                                    "venue": {"displayName": "Stereo"},
                                    "location": {"city": "Glasgow, UK", "lat": 55.86, "lng": -4.25},
                                    "performance": [{"displayName": "Sample Artist"}],
                                }
                            ]
                        },
                    }
                }
            ).encode("utf-8")

    monkeypatch.setattr("app.sources.songkick.urlopen", lambda request, timeout: FakeResponse())

    result = SongkickAdapter().fetch(
        GLASGOW_CONFIG,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )

    assert result.events[0].source_event_id == "1"
    assert result.events[0].source_attribution == "Songkick API"
    assert result.events[0].venue_name == "Stereo"


def test_public_rss_and_ical_parsers_normalise_events() -> None:
    rss = """
    <rss><channel><item><title>RSS Gig</title><link>https://example.test/rss-gig</link>
    <pubDate>Fri, 05 Jun 2026 19:30:00 GMT</pubDate><description>Venue: Mono</description></item></channel></rss>
    """
    ical = """
    BEGIN:VCALENDAR
    BEGIN:VEVENT
    UID:ical-1
    SUMMARY:iCal Gig
    DTSTART:20260605T193000Z
    LOCATION:Stereo
    URL:https://example.test/ical-gig
    END:VEVENT
    END:VCALENDAR
    """

    rss_events = parse_rss_events(rss, "RSS Feed", "https://example.test/feed.xml")
    ical_events = parse_ical_events(ical, "iCal Feed", "https://example.test/feed.ics")

    assert rss_events[0].venue_name == "Mono"
    assert rss_events[0].source_kind == "rss"
    assert ical_events[0].source_event_id == "ical-1"
    assert ical_events[0].source_kind == "ical"


def test_structured_data_parser_extracts_json_ld_event() -> None:
    html = """
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Event","name":"Structured Gig","startDate":"2026-06-05T19:30:00+00:00",
    "location":{"@type":"Place","name":"The Hug and Pint","address":{"@type":"PostalAddress","streetAddress":"171 Great Western Road","addressLocality":"Glasgow","postalCode":"G4 9AW"}},
    "offers":{"url":"https://example.test/tickets"}}
    </script>
    """

    events = extract_json_ld_events(html, "Venue JSON-LD", "https://venue.example/events")

    assert events[0].title == "Structured Gig"
    assert events[0].venue_name == "The Hug and Pint"
    assert events[0].venue_postcode == "G4 9AW"


def test_glasgow_venue_coverage_seed_contains_requested_venues() -> None:
    seed_path = Path("seeds/glasgow_venue_coverage.json")
    venues = json.loads(seed_path.read_text(encoding="utf-8"))
    names = {venue["name"] for venue in venues}

    assert len(venues) == 45
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
        "The Blue Arrow",
        "The Admiral",
        "The Flying Duck",
        "Bloc+",
        "The 13th Note",
        "The Poetry Club",
        "Cottiers",
        "Mackintosh Queen's Cross",
        "The Stand Glasgow",
        "The Old Fruitmarket",
        "City Halls",
        "Òran Mór Auditorium",
        "Websters Theatre",
        "Òran Mór Whisky Bar",
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
