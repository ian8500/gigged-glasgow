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


class TicketmasterDiscoveryAdapter(SourceAdapterBase):
    name = "Ticketmaster Discovery API"
    slug = "ticketmaster"
    kind = "api"
    requires_credentials = True
    required_settings = ["ticketmaster_api_key"]
    official_api_available = "yes"
    automation_allowed = "yes"
    terms_reviewed = True
    current_mode = "working"
    limitations = "Official Discovery API; broad commercial ticketing coverage, not complete Glasgow coverage."
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    page_size = 200

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key or settings.ticketmaster_api_key)

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        if city.slug != "glasgow":
            return SourceFetchResult(
                source_name=self.name,
                warnings=["Ticketmaster Phase 1 ingestion is restricted to Glasgow."],
            )
        api_key = self.api_key or settings.ticketmaster_api_key
        if not api_key:
            return SourceFetchResult(
                source_name=self.name,
                warnings=["TICKETMASTER_API_KEY is not set; Ticketmaster ingestion skipped."],
            )

        events: list[NormalizedSourceEvent] = []
        warnings: list[str] = []
        failures: list[str] = []
        page = 0
        total_pages = 1

        while page < total_pages:
            payload, error = self._fetch_page(start, end, page, api_key)
            if error:
                failures.append(error)
                break

            raw_events = payload.get("_embedded", {}).get("events", [])
            for item in raw_events:
                event = self._normalise(item)
                if event is None:
                    warnings.append("Ticketmaster event skipped because it had no usable start date.")
                    continue
                events.append(event)

            page_info = payload.get("page") or {}
            total_pages = min(int(page_info.get("totalPages") or 1), 5)
            page += 1

        return SourceFetchResult(
            source_name=self.name,
            events=events,
            warnings=warnings,
            failures=failures,
        )

    def test_connection(self) -> tuple[bool, str]:
        api_key = self.api_key or settings.ticketmaster_api_key
        if not api_key:
            return False, "Ticketmaster API key is not configured."
        now = datetime.now(timezone.utc)
        payload, error = self._fetch_page(now, now, 0, api_key, size=1)
        if error:
            return False, error
        return True, f"Ticketmaster connection succeeded; API returned page metadata {payload.get('page', {})}."

    def _fetch_page(
        self,
        start: datetime,
        end: datetime,
        page: int,
        api_key: str,
        size: int | None = None,
    ) -> tuple[dict, str | None]:
        params = {
            "apikey": api_key,
            "city": "Glasgow",
            "countryCode": "GB",
            "classificationName": "music",
            "startDateTime": _as_ticketmaster_datetime(start),
            "endDateTime": _as_ticketmaster_datetime(end),
            "size": str(size or self.page_size),
            "page": str(page),
            "sort": "date,asc",
            "includeTBA": "no",
            "includeTBD": "no",
        }
        url = f"{self.base_url}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "GiggedGlasgow/0.1"})

        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as exc:
            return {}, f"Ticketmaster returned HTTP {exc.code}; ingestion stopped."
        except URLError as exc:
            return {}, f"Ticketmaster request failed: {exc.reason}"

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        return self._normalise(item)

    def _normalise(self, item: dict) -> NormalizedSourceEvent | None:
        dates = item.get("dates", {})
        start_info = dates.get("start", {})
        start_value = start_info.get("dateTime") or start_info.get("localDate")
        if not start_value:
            return None

        starts_at = isoparse(start_value)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)

        embedded = item.get("_embedded", {})
        venue = (embedded.get("venues") or [{}])[0]
        attractions = embedded.get("attractions") or []
        artist_name = attractions[0].get("name") if attractions else item.get("name")
        classifications = item.get("classifications") or []
        genre = None
        if classifications:
            genre = (classifications[0].get("genre") or {}).get("name")

        price_ranges = item.get("priceRanges") or []
        price_min = _decimal_or_none(price_ranges[0].get("min")) if price_ranges else None
        price_max = _decimal_or_none(price_ranges[0].get("max")) if price_ranges else None
        currency = price_ranges[0].get("currency", "GBP") if price_ranges else "GBP"
        images = sorted(item.get("images") or [], key=lambda image: image.get("width", 0), reverse=True)

        return NormalizedSourceEvent(
            title=item.get("name", "Untitled event"),
            artist_name=artist_name,
            venue_name=venue.get("name", "Venue TBC"),
            starts_at=starts_at,
            ticket_url=item.get("url"),
            source_url=item.get("url"),
            image_url=images[0].get("url") if images else None,
            price_min=price_min,
            price_max=price_max,
            currency=currency,
            genre=genre,
            status=(dates.get("status") or {}).get("code", "scheduled"),
            source_name=self.name,
            source_kind=self.kind,
            source_event_id=item.get("id"),
            source_attribution="Ticketmaster Discovery API",
            raw_payload=item,
            confidence_hints={
                "has_source_id": bool(item.get("id")),
                "has_ticket_url": bool(item.get("url")),
                "has_artist": bool(artist_name),
                "has_venue": bool(venue.get("name")),
                "has_datetime": bool(start_info.get("dateTime")),
            },
        )


def _as_ticketmaster_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
