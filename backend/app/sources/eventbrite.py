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


class EventbriteAdapter(SourceAdapterBase):
    name = "Eventbrite"
    slug = "eventbrite"
    kind = "api"
    requires_credentials = True
    required_settings = ["eventbrite_api_key"]
    official_api_available = "limited"
    automation_allowed = "yes"
    terms_reviewed = True
    current_mode = "configured_disabled"
    limitations = (
        "Uses official Eventbrite API only. Public discovery can be unavailable for some "
        "tokens/accounts; the adapter reports that instead of scraping."
    )
    api_base_url = "https://www.eventbriteapi.com/v3"
    search_path = "/events/search/"
    page_size = 50

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key or settings.eventbrite_api_key)

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        if city.slug != "glasgow":
            return SourceFetchResult(
                source_name=self.name,
                warnings=["Eventbrite ingestion currently supports Glasgow only."],
            )

        api_key = self.api_key or settings.eventbrite_api_key
        if not api_key:
            return SourceFetchResult(
                source_name=self.name,
                warnings=["EVENTBRITE_API_KEY is not set; Eventbrite ingestion skipped."],
            )

        events: list[NormalizedSourceEvent] = []
        warnings: list[str] = []
        failures: list[str] = []
        continuation: str | None = None
        pages_checked = 0

        while pages_checked < 5:
            payload, error, discovery_unavailable = self._fetch_search_page(city, start, end, api_key, continuation)
            if error:
                if discovery_unavailable:
                    warnings.append(error)
                else:
                    failures.append(error)
                break

            for item in payload.get("events") or []:
                event = self._normalise(item)
                if event is None:
                    warnings.append("Eventbrite event skipped because it had no usable start date.")
                    continue
                events.append(event)

            pagination = payload.get("pagination") or {}
            if not pagination.get("has_more_items"):
                break
            continuation = pagination.get("continuation")
            if not continuation:
                break
            pages_checked += 1

        return SourceFetchResult(
            source_name=self.name,
            events=events,
            warnings=warnings,
            failures=failures,
        )

    def test_connection(self) -> tuple[bool, str]:
        api_key = self.api_key or settings.eventbrite_api_key
        if not api_key:
            return False, "Eventbrite API token is not configured."
        payload, error = self._get("/users/me/", api_key)
        if error:
            return False, error
        user_id = payload.get("id")
        email = payload.get("emails", [{}])[0].get("email") if payload.get("emails") else None
        identity = email or payload.get("name") or user_id or "current user"
        return True, f"Eventbrite token valid for {identity}."

    def _fetch_search_page(
        self,
        city: CityConfig,
        start: datetime,
        end: datetime,
        api_key: str,
        continuation: str | None = None,
    ) -> tuple[dict, str | None, bool]:
        params = {
            "q": "music gig concert",
            "location.address": "Glasgow, Scotland, United Kingdom",
            "location.within": f"{city.search_radius_km}km",
            "categories": "103",
            "start_date.range_start": _as_eventbrite_datetime(start),
            "start_date.range_end": _as_eventbrite_datetime(end),
            "expand": "venue,category,ticket_availability,organizer",
            "sort_by": "date",
            "page_size": str(self.page_size),
        }
        if continuation:
            params["continuation"] = continuation
        payload, error = self._get(self.search_path, api_key, params)
        if error and ("HTTP 403" in error or "HTTP 404" in error):
            token_ok, token_message = self.test_connection()
            if not token_ok:
                return {}, f"Eventbrite public discovery failed and the token could not be validated: {token_message}", False
            return (
                {},
                "Eventbrite token valid, but public discovery is unavailable for this token/account.",
                True,
            )
        return payload, error, False

    def _get(
        self,
        path: str,
        api_key: str,
        params: dict[str, str] | None = None,
    ) -> tuple[dict, str | None]:
        url = f"{self.api_base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "GiggedGlasgow/0.1",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as exc:
            detail = _eventbrite_error_detail(exc)
            return {}, f"Eventbrite returned HTTP {exc.code}{detail}."
        except URLError as exc:
            return {}, f"Eventbrite request failed: {exc.reason}"

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        return self._normalise(item)

    def _normalise(self, item: dict) -> NormalizedSourceEvent | None:
        start_info = item.get("start") or {}
        start_value = start_info.get("utc") or start_info.get("local")
        if not start_value:
            return None
        starts_at = isoparse(start_value)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)

        end_info = item.get("end") or {}
        end_value = end_info.get("utc") or end_info.get("local")
        ends_at = isoparse(end_value) if end_value else None
        if ends_at and ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)

        venue = item.get("venue") or {}
        address = venue.get("address") or {}
        category = item.get("category") or {}
        ticket_availability = item.get("ticket_availability") or {}
        minimum_price = ticket_availability.get("minimum_ticket_price") or {}
        maximum_price = ticket_availability.get("maximum_ticket_price") or {}
        name = _text_field(item.get("name")) or "Untitled Eventbrite event"
        organizer = item.get("organizer") or {}
        logo = item.get("logo") or {}
        image_url = (logo.get("original") or {}).get("url") or logo.get("url")

        return NormalizedSourceEvent(
            title=name,
            description=_text_field(item.get("description")) or _text_field(item.get("summary")),
            artist_name=organizer.get("name") or name,
            venue_name=venue.get("name") or "Venue TBC",
            starts_at=starts_at,
            ends_at=ends_at,
            ticket_url=item.get("url"),
            source_url=item.get("url") or item.get("resource_uri"),
            image_url=image_url,
            venue_address=address.get("localized_address_display") or address.get("address_1"),
            venue_postcode=address.get("postal_code"),
            city=address.get("city") or "Glasgow",
            latitude=_float_or_none(address.get("latitude")),
            longitude=_float_or_none(address.get("longitude")),
            price_min=_money_to_decimal(minimum_price),
            price_max=_money_to_decimal(maximum_price),
            currency=minimum_price.get("currency") or maximum_price.get("currency") or item.get("currency") or "GBP",
            genre=category.get("name") or category.get("short_name"),
            status=item.get("status") or "scheduled",
            source_name=self.name,
            source_kind=self.kind,
            source_event_id=item.get("id"),
            source_attribution="Eventbrite API",
            raw_payload=item,
            confidence_hints={
                "has_source_id": bool(item.get("id")),
                "has_ticket_url": bool(item.get("url")),
                "has_artist": bool(organizer.get("name")),
                "has_venue": bool(venue.get("name")),
                "has_datetime": bool(start_info.get("utc") or start_info.get("local")),
            },
        )


def _as_eventbrite_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _money_to_decimal(value: dict) -> Decimal | None:
    major_value = value.get("major_value")
    if major_value is None:
        return None
    return Decimal(str(major_value))


def _text_field(value: object) -> str | None:
    if isinstance(value, dict):
        return value.get("text")
    if isinstance(value, str):
        return value
    return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _eventbrite_error_detail(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return ""
    message = payload.get("error_description") or payload.get("error") or payload.get("status_description")
    return f": {message}" if message else ""
