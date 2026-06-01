from __future__ import annotations

from datetime import datetime

from app.cities.base import CityConfig
from app.sources.base import SourceAdapterBase, SourceFetchResult


class PublicVenuePageAdapter(SourceAdapterBase):
    name = "Official venue structured data"
    slug = "official-venue-structured-data"
    kind = "venue_feed"
    current_mode = "manual_only"
    official_api_available = "unknown"
    automation_allowed = "conditional"
    terms_reviewed = False
    limitations = (
        "Safe structured-data framework only. It fetches public pages when allowed and looks "
        "for JSON-LD Event data or feed links; no browser automation or anti-bot bypass."
    )

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        return SourceFetchResult(
            source_name=self.name,
            warnings=[
                "Venue structured-data adapter framework is available per venue; configure official_events_url/feed_url and run venue checks."
            ],
        )
