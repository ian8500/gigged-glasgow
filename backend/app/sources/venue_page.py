from __future__ import annotations

from datetime import datetime

from app.cities.base import CityConfig
from app.sources.base import EventSourceAdapter, SourceFetchResult


class PublicVenuePageAdapter(EventSourceAdapter):
    name = "Public venue pages"
    kind = "venue_page"

    def fetch(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        return SourceFetchResult(
            source_name=self.name,
            warnings=[
                "Venue page adapter placeholder only. Before implementation, review each venue's robots.txt, terms, rate limits, and permitted reuse. Do not bypass login, paywalls, bot controls, or disallowed paths."
            ],
        )

