from __future__ import annotations

from datetime import datetime

from app.cities.base import CityConfig
from app.sources.base import EventSourceAdapter, SourceFetchResult


class EventbriteAdapter(EventSourceAdapter):
    name = "Eventbrite"
    kind = "api"

    def fetch(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        return SourceFetchResult(
            source_name=self.name,
            warnings=[
                "Eventbrite adapter placeholder only. Add official API credentials and terms review before enabling."
            ],
        )
