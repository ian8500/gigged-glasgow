from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dateutil.parser import isoparse

from app.cities.base import CityConfig
from app.core.settings import settings
from app.sources.base import NormalizedSourceEvent, SourceAdapterBase, SourceFetchResult


class SongkickAdapter(SourceAdapterBase):
    name = "Songkick"
    slug = "songkick"
    kind = "partner"
    requires_credentials = True
    required_settings = ["songkick_api_key", "songkick_partner_mode", "songkick_metro_area_id"]
    official_api_available = "partner"
    automation_allowed = "partner"
    terms_reviewed = True
    current_mode = "partner_access_required"
    limitations = "Partner/licensed access required. Do not fake Songkick API availability."
    base_url = "https://api.songkick.com/api/3.0"

    def __init__(
        self,
        api_key: str | None = None,
        partner_mode: bool | None = None,
        metro_area_id: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.partner_mode = partner_mode
        self.metro_area_id = metro_area_id

    def is_configured(self) -> bool:
        partner_mode = self.partner_mode if self.partner_mode is not None else settings.songkick_partner_mode
        return bool(partner_mode and (self.api_key or settings.songkick_api_key) and (self.metro_area_id or settings.songkick_metro_area_id))

    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "Partner/licensed access required."
        now = datetime.now(timezone.utc)
        payload, error = self._fetch_page(now, now, page=1, per_page=1)
        if error:
            return False, error
        results = payload.get("resultsPage", {})
        return True, f"Songkick connection succeeded; status {results.get('status', 'ok')}."

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        if city.slug != "glasgow":
            return SourceFetchResult(source_name=self.name, warnings=["Songkick ingestion currently supports Glasgow only."])
        if not self.is_configured():
            return SourceFetchResult(source_name=self.name, warnings=["Partner/licensed access required."])

        events: list[NormalizedSourceEvent] = []
        failures: list[str] = []
        page = 1
        total_pages = 1
        while page <= total_pages and page <= 5:
            payload, error = self._fetch_page(start, end, page=page, per_page=50)
            if error:
                failures.append(error)
                break
            results_page = payload.get("resultsPage") or {}
            results = results_page.get("results") or {}
            for item in results.get("event") or []:
                event = self.normalize_event(item)
                if event:
                    events.append(event)
            per_page = int(results_page.get("perPage") or 50)
            total_entries = int(results_page.get("totalEntries") or 0)
            total_pages = max(1, (total_entries + per_page - 1) // per_page)
            page += 1
        return SourceFetchResult(source_name=self.name, events=events, failures=failures)

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        start = item.get("start") or {}
        start_value = start.get("datetime") or start.get("date")
        if not start_value:
            return None
        starts_at = isoparse(start_value)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        venue = item.get("venue") or {}
        location = item.get("location") or {}
        performance = item.get("performance") or []
        artist = (performance[0] or {}).get("displayName") if performance else item.get("displayName")

        return NormalizedSourceEvent(
            title=item.get("displayName") or "Untitled Songkick event",
            artist_name=artist,
            venue_name=venue.get("displayName") or "Venue TBC",
            city=location.get("city"),
            latitude=_float_or_none(location.get("lat")),
            longitude=_float_or_none(location.get("lng")),
            starts_at=starts_at,
            ticket_url=item.get("uri"),
            source_url=item.get("uri"),
            source_name=self.name,
            source_kind=self.kind,
            source_event_id=str(item.get("id")) if item.get("id") else None,
            source_attribution="Songkick API",
            raw_payload=item,
            confidence_hints={
                "has_source_id": bool(item.get("id")),
                "has_ticket_url": bool(item.get("uri")),
                "has_artist": bool(artist),
                "has_venue": bool(venue.get("displayName")),
                "has_datetime": bool(start.get("datetime")),
            },
        )

    def _fetch_page(self, start: datetime, end: datetime, page: int, per_page: int) -> tuple[dict, str | None]:
        api_key = self.api_key or settings.songkick_api_key
        metro_area_id = self.metro_area_id or settings.songkick_metro_area_id
        if not api_key or not metro_area_id:
            return {}, "Partner/licensed access required."
        params = {
            "apikey": api_key,
            "min_date": start.date().isoformat(),
            "max_date": end.date().isoformat(),
            "page": str(page),
            "per_page": str(per_page),
        }
        url = f"{self.base_url}/metro_areas/{metro_area_id}/calendar.json?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "GiggedGlasgow/0.1"})
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as exc:
            return {}, f"Songkick returned HTTP {exc.code}; partner/licensed access may be missing."
        except URLError as exc:
            return {}, f"Songkick request failed: {exc.reason}"


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None
