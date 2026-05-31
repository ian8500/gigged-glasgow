from __future__ import annotations

from datetime import datetime

from app.cities.base import CityConfig
from app.sources.base import EventSourceAdapter, SourceFetchResult


class SongkickAdapter(EventSourceAdapter):
    name = "Songkick"
    kind = "api"

    def fetch(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        return SourceFetchResult(
            source_name=self.name,
            warnings=[
                "Songkick adapter placeholder only. Add official API credentials and terms review before enabling."
            ],
        )

