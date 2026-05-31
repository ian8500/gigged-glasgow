from __future__ import annotations

from datetime import date, datetime, timezone

from app.services.normalization import fingerprint_parts
from app.services.weekly import next_friday_to_thursday


def test_fingerprint_uses_city_artist_venue_and_date() -> None:
    fingerprint = fingerprint_parts(
        city_slug="glasgow",
        artist_name="Sample Artist",
        venue_name="King Tut's Wah Wah Hut",
        starts_at=datetime(2026, 6, 5, 19, 30, tzinfo=timezone.utc),
    )

    assert fingerprint == "glasgow-sample-artist-king-tuts-wah-wah-hut-2026-06-05"


def test_weekly_window_runs_friday_to_thursday() -> None:
    starts_on, ends_on = next_friday_to_thursday(date(2026, 5, 31))

    assert starts_on == date(2026, 6, 5)
    assert ends_on == date(2026, 6, 11)

