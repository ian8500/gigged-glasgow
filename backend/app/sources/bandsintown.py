from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from dateutil.parser import isoparse

from app.cities.base import CityConfig
from app.core.settings import settings
from app.sources.base import NormalizedSourceEvent, SourceAdapterBase, SourceFetchResult


class BandsintownAdapter(SourceAdapterBase):
    name = "Bandsintown"
    slug = "bandsintown"
    kind = "api"
    requires_credentials = True
    required_settings = ["bandsintown_app_id", "bandsintown_artist_seed_list"]
    official_api_available = "yes"
    automation_allowed = "yes"
    terms_reviewed = True
    current_mode = "configured_disabled"
    limitations = "Artist-seed based; not complete city-wide discovery."
    base_url = "https://rest.bandsintown.com"

    def __init__(self, app_id: str | None = None, artist_seed_list: str | None = None) -> None:
        self.app_id = app_id
        self.artist_seed_list = artist_seed_list

    def is_configured(self) -> bool:
        return bool(self.app_id or settings.bandsintown_app_id)

    def source_notes(self) -> str:
        return "Bandsintown is artist-seed based, not complete city-wide discovery."

    def test_connection(self) -> tuple[bool, str]:
        app_id = self.app_id or settings.bandsintown_app_id
        if not app_id:
            return False, "Bandsintown app_id is not configured."
        artist = self._artist_seeds(None)[0] if self._artist_seeds(None) else "Mogwai"
        payload, error = self._get_artist_events(artist, app_id, datetime.now(timezone.utc), datetime.now(timezone.utc))
        if error:
            return False, error
        if isinstance(payload, list):
            return True, "Bandsintown connection succeeded. Artist-event API is reachable."
        return False, "Bandsintown returned an unexpected response."

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        app_id = self.app_id or settings.bandsintown_app_id
        if not app_id:
            return SourceFetchResult(source_name=self.name, warnings=["BANDSINTOWN_APP_ID is not set; Bandsintown skipped."])

        events: list[NormalizedSourceEvent] = []
        warnings: list[str] = []
        failures: list[str] = []
        for artist in self._artist_seeds(city):
            payload, error = self._get_artist_events(artist, app_id, start, end)
            if error:
                failures.append(error)
                continue
            for item in payload if isinstance(payload, list) else []:
                event = self.normalize_event(item)
                if event is None:
                    continue
                if _is_glasgow_event(event):
                    events.append(event)

        if not self._artist_seeds(city):
            warnings.append("No Bandsintown artist seed list is configured; source skipped.")
        return SourceFetchResult(source_name=self.name, events=events, warnings=warnings, failures=failures)

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        start_value = item.get("datetime") or item.get("starts_at")
        if not start_value:
            return None
        starts_at = isoparse(start_value)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        venue = item.get("venue") or {}
        artist = (item.get("lineup") or [None])[0] or item.get("artist") or item.get("title")
        offers = item.get("offers") or []
        ticket_url = (offers[0] or {}).get("url") if offers else item.get("url")

        return NormalizedSourceEvent(
            title=item.get("title") or f"{artist} at {venue.get('name', 'Venue TBC')}",
            artist_name=artist,
            description=item.get("description"),
            venue_name=venue.get("name") or "Venue TBC",
            venue_address=venue.get("street_address"),
            venue_postcode=venue.get("postal_code"),
            city=venue.get("city"),
            latitude=_float_or_none(venue.get("latitude")),
            longitude=_float_or_none(venue.get("longitude")),
            starts_at=starts_at,
            ticket_url=ticket_url,
            source_url=item.get("url") or ticket_url,
            source_name=self.name,
            source_kind=self.kind,
            source_event_id=str(item.get("id")) if item.get("id") else None,
            source_attribution="Bandsintown API",
            raw_payload=item,
            confidence_hints={
                "has_source_id": bool(item.get("id")),
                "has_ticket_url": bool(ticket_url),
                "has_artist": bool(artist),
                "has_venue": bool(venue.get("name")),
                "has_datetime": True,
            },
        )

    def _artist_seeds(self, city: CityConfig | None) -> list[str]:
        raw = self.artist_seed_list or settings.bandsintown_artist_seed_list or ""
        return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]

    def _get_artist_events(
        self,
        artist: str,
        app_id: str,
        start: datetime,
        end: datetime,
    ) -> tuple[object, str | None]:
        params = {
            "app_id": app_id,
            "date": f"{start.date().isoformat()},{end.date().isoformat()}",
        }
        url = f"{self.base_url}/artists/{quote(artist)}/events?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "GiggedGlasgow/0.1"})
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as exc:
            return [], f"Bandsintown returned HTTP {exc.code} for {artist}."
        except URLError as exc:
            return [], f"Bandsintown request failed for {artist}: {exc.reason}"


def _is_glasgow_event(event: NormalizedSourceEvent) -> bool:
    haystack = " ".join(
        value.lower()
        for value in [event.city, event.venue_name, event.venue_address, event.venue_postcode]
        if value
    )
    return "glasgow" in haystack or "g1" in haystack or "g2" in haystack or "g3" in haystack or "g4" in haystack


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None
