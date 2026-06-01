from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from datetime import timezone
from html.parser import HTMLParser
from urllib.parse import urljoin

from dateutil.parser import isoparse

from app.sources.base import NormalizedSourceEvent


def extract_json_ld_events(html: str, source_name: str, source_url: str) -> list[NormalizedSourceEvent]:
    events: list[NormalizedSourceEvent] = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        for item in _walk_json_ld(payload):
            event = _normalise_schema_event(item, source_name, source_url)
            if event:
                events.append(event)
    return events


def extract_microdata_events(html: str, source_name: str, source_url: str) -> list[NormalizedSourceEvent]:
    parser = _MicrodataEventParser(source_name=source_name, source_url=source_url)
    parser.feed(html)
    return parser.events


def _walk_json_ld(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for entry in payload for item in _walk_json_ld(entry)]
    if not isinstance(payload, dict):
        return []
    graph = payload.get("@graph")
    if graph:
        return _walk_json_ld(graph)
    item_type = payload.get("@type")
    if item_type == "Event" or (isinstance(item_type, list) and "Event" in item_type):
        return [payload]
    for key in ("event", "events", "mainEntity", "itemListElement"):
        child = payload.get(key)
        if child:
            return _walk_json_ld(child)
    return []


def _normalise_schema_event(item: dict, source_name: str, source_url: str) -> NormalizedSourceEvent | None:
    start_value = item.get("startDate")
    if not item.get("name") or not start_value:
        return None
    try:
        starts_at = isoparse(start_value)
    except (TypeError, ValueError):
        return None
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    ends_at = None
    if item.get("endDate"):
        try:
            ends_at = isoparse(item["endDate"])
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            ends_at = None
    location = item.get("location") or {}
    address = location.get("address") if isinstance(location.get("address"), dict) else {}
    image = item.get("image")
    offers = _first_dict(item.get("offers")) or {}
    performer = item.get("performer")
    artist_name = None
    if isinstance(performer, dict):
        artist_name = performer.get("name")
    elif isinstance(performer, list) and performer and isinstance(performer[0], dict):
        artist_name = performer[0].get("name")

    price = _decimal_or_none(offers.get("price") or offers.get("lowPrice"))
    currency = offers.get("priceCurrency") or item.get("priceCurrency") or "GBP"

    return NormalizedSourceEvent(
        title=item.get("name"),
        artist_name=artist_name or item.get("name"),
        description=item.get("description"),
        venue_name=location.get("name") if isinstance(location, dict) and location.get("name") else "Venue TBC",
        venue_address=address.get("streetAddress"),
        venue_postcode=address.get("postalCode"),
        city=address.get("addressLocality"),
        starts_at=starts_at,
        ends_at=ends_at,
        ticket_url=offers.get("url") or item.get("url"),
        source_url=item.get("url") or source_url,
        image_url=image[0] if isinstance(image, list) and image else image if isinstance(image, str) else None,
        price_min=price,
        price_max=_decimal_or_none(offers.get("highPrice")),
        currency=currency,
        source_name=source_name,
        source_kind="venue_feed",
        source_event_id=item.get("@id") or item.get("url"),
        source_attribution=source_name,
        raw_payload=item,
        confidence_hints={
            "has_source_id": bool(item.get("@id") or item.get("url")),
            "has_ticket_url": bool(offers.get("url") or item.get("url")),
            "has_artist": bool(artist_name),
            "has_venue": bool(isinstance(location, dict) and location.get("name")),
            "has_datetime": True,
        },
    )


def _first_dict(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), None)
    return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        return Decimal(str(value).replace("£", "").strip())
    except (InvalidOperation, ValueError):
        return None


class _MicrodataEventParser(HTMLParser):
    def __init__(self, source_name: str, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_name = source_name
        self.source_url = source_url
        self.in_event = False
        self.depth = 0
        self.current: dict[str, str] = {}
        self.prop_stack: list[str | None] = []
        self.events: list[NormalizedSourceEvent] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        itemtype = attributes.get("itemtype", "")
        if not self.in_event and "schema.org/event" in itemtype.lower():
            self.in_event = True
            self.depth = 1
            self.current = {}
        elif self.in_event:
            self.depth += 1

        prop = attributes.get("itemprop") if self.in_event else None
        self.prop_stack.append(prop)
        if not self.in_event or not prop:
            return

        value = (
            attributes.get("content")
            or attributes.get("datetime")
            or attributes.get("href")
            or attributes.get("src")
            or attributes.get("alt")
        )
        if value:
            self.current[prop] = urljoin(self.source_url, value) if prop in {"url", "image"} else value

    def handle_data(self, data: str) -> None:
        if not self.in_event or not self.prop_stack:
            return
        prop = self.prop_stack[-1]
        text = " ".join(data.split())
        if prop and text and prop not in self.current:
            self.current[prop] = text

    def handle_endtag(self, tag: str) -> None:
        if self.prop_stack:
            self.prop_stack.pop()
        if not self.in_event:
            return
        self.depth -= 1
        if self.depth <= 0:
            event = _normalise_schema_event(
                {
                    "@type": "Event",
                    "name": self.current.get("name"),
                    "startDate": self.current.get("startDate"),
                    "endDate": self.current.get("endDate"),
                    "description": self.current.get("description"),
                    "url": self.current.get("url"),
                    "image": self.current.get("image"),
                    "location": {"name": self.current.get("location") or "Venue TBC"},
                    "offers": {
                        "url": self.current.get("url"),
                        "price": self.current.get("price"),
                        "priceCurrency": self.current.get("priceCurrency") or "GBP",
                    },
                },
                self.source_name,
                self.source_url,
            )
            if event:
                self.events.append(event)
            self.in_event = False
            self.depth = 0
            self.current = {}
