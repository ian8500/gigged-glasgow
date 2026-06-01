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


class SkiddleAdapter(SourceAdapterBase):
    name = "Skiddle"
    slug = "skiddle"
    kind = "partner_api"
    requires_credentials = True
    required_settings = ["skiddle_api_key", "skiddle_city_id", "skiddle_api_base_url"]
    official_api_available = "partner"
    automation_allowed = "conditional"
    terms_reviewed = False
    current_mode = "partner_access_required"
    limitations = (
        "Skiddle ingestion is disabled unless an approved API or partner feed endpoint is configured. "
        "Do not scrape Skiddle web pages."
    )

    def __init__(
        self,
        api_key: str | None = None,
        city_id: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.city_id = city_id
        self.api_base_url = api_base_url

    def is_configured(self) -> bool:
        return bool(
            (self.api_key or settings.skiddle_api_key)
            and (self.city_id or settings.skiddle_city_id)
            and (self.api_base_url or settings.skiddle_api_base_url)
        )

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        if city.slug != "glasgow":
            return SourceFetchResult(source_name=self.name, warnings=["Skiddle Phase 1 ingestion is restricted to Glasgow."])
        if not self.is_configured():
            return SourceFetchResult(
                source_name=self.name,
                warnings=["Skiddle partner/API settings are not configured; source skipped."],
            )

        payload, error = self._fetch_partner_payload(start, end)
        if error:
            return SourceFetchResult(source_name=self.name, failures=[error])

        raw_events = payload.get("events") or payload.get("results") or []
        events: list[NormalizedSourceEvent] = []
        warnings: list[str] = []
        for item in raw_events if isinstance(raw_events, list) else []:
            event = self.normalize_event(item)
            if event is None:
                warnings.append("Skiddle event skipped because it had no usable title, venue, or date.")
                continue
            events.append(event)
        return SourceFetchResult(source_name=self.name, events=events, warnings=warnings)

    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "Skiddle partner/API settings are not configured."
        now = datetime.now(timezone.utc)
        _payload, error = self._fetch_partner_payload(now, now)
        if error:
            return False, error
        return True, "Skiddle partner/API endpoint is reachable."

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        title = str(item.get("eventname") or item.get("title") or item.get("name") or "").strip()
        venue = item.get("venue") or {}
        venue_name = str(
            venue.get("name") if isinstance(venue, dict) else item.get("venue_name") or item.get("venue")
        ).strip()
        starts_at_raw = item.get("date") or item.get("startdate") or item.get("starts_at") or item.get("datetime")
        if not title or not venue_name or not starts_at_raw:
            return None

        starts_at = isoparse(str(starts_at_raw))
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)

        event_id = item.get("id") or item.get("event_id")
        ticket_url = item.get("link") or item.get("ticket_url") or item.get("url")
        image_url = item.get("imageurl") or item.get("image_url")
        artist = item.get("artist") or item.get("artists") or title
        if isinstance(artist, list):
            artist = ", ".join(str(value) for value in artist if value)

        return NormalizedSourceEvent(
            title=title,
            artist_name=str(artist) if artist else title,
            venue_name=venue_name,
            venue_address=venue.get("address") if isinstance(venue, dict) else item.get("venue_address"),
            venue_postcode=venue.get("postcode") if isinstance(venue, dict) else item.get("postcode"),
            starts_at=starts_at,
            ticket_url=ticket_url,
            source_url=item.get("source_url") or ticket_url,
            image_url=image_url,
            price_min=_decimal_or_none(item.get("minprice") or item.get("price_min")),
            price_max=_decimal_or_none(item.get("maxprice") or item.get("price_max")),
            genre=item.get("genre") or item.get("category"),
            source_name=self.name,
            source_kind=self.kind,
            source_event_id=str(event_id) if event_id else None,
            source_attribution="Skiddle partner/API feed",
            raw_payload=item,
            confidence_hints={
                "has_source_id": bool(event_id),
                "has_ticket_url": bool(ticket_url),
                "has_artist": bool(artist),
                "has_venue": bool(venue_name),
                "has_datetime": True,
            },
        )

    def _fetch_partner_payload(self, start: datetime, end: datetime) -> tuple[dict, str | None]:
        base_url = self.api_base_url or settings.skiddle_api_base_url
        api_key = self.api_key or settings.skiddle_api_key
        city_id = self.city_id or settings.skiddle_city_id
        if not base_url or not api_key or not city_id:
            return {}, "Skiddle partner/API settings are incomplete."
        params = {
            "api_key": api_key,
            "city_id": city_id,
            "minDate": start.date().isoformat(),
            "maxDate": end.date().isoformat(),
        }
        separator = "&" if "?" in base_url else "?"
        request = Request(
            f"{base_url}{separator}{urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": "GiggedGlasgow/0.1"},
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as exc:
            return {}, f"Skiddle partner/API endpoint returned HTTP {exc.code}."
        except URLError as exc:
            return {}, f"Skiddle partner/API request failed: {exc.reason}"


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, ""}:
        return None
    return Decimal(str(value))
