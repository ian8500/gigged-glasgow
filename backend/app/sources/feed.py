from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dateutil.parser import isoparse, parse as parse_datetime

from app.sources.base import NormalizedSourceEvent, SourceFetchResult


def fetch_feed_events(feed_url: str, feed_type: str, source_name: str = "Public feed") -> SourceFetchResult:
    request = Request(feed_url, headers={"User-Agent": "GiggedGlasgow/0.1", "Accept": "*/*"})
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return SourceFetchResult(source_name=source_name, failures=[f"Feed returned HTTP {exc.code}."])
    except URLError as exc:
        return SourceFetchResult(source_name=source_name, failures=[f"Feed request failed: {exc.reason}"])

    if feed_type == "ical":
        events = parse_ical_events(raw, source_name, feed_url)
    else:
        events = parse_rss_events(raw, source_name, feed_url)
    warnings = []
    for event in events:
        if event.venue_name == "Venue TBC" or not event.starts_at:
            warnings.append(f"{event.title} needs review because the feed was missing venue/date detail.")
    return SourceFetchResult(source_name=source_name, events=events, warnings=warnings)


def parse_rss_events(raw: str, source_name: str, feed_url: str) -> list[NormalizedSourceEvent]:
    root = ET.fromstring(raw)
    events: list[NormalizedSourceEvent] = []
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for item in items:
        title = _xml_text(item, "title") or _xml_text(item, "{http://www.w3.org/2005/Atom}title")
        link = _xml_text(item, "link") or _atom_link(item)
        description = _xml_text(item, "description") or _xml_text(item, "summary") or _xml_text(item, "{http://www.w3.org/2005/Atom}summary")
        date_value = (
            _xml_text(item, "pubDate")
            or _xml_text(item, "date")
            or _xml_text(item, "{http://www.w3.org/2005/Atom}updated")
            or _xml_text(item, "{http://www.w3.org/2005/Atom}published")
        )
        starts_at = _parse_feed_datetime(date_value or "")
        if not title or not starts_at:
            continue
        venue_name = _extract_location(description or "") or "Venue TBC"
        events.append(
            NormalizedSourceEvent(
                title=title,
                artist_name=title,
                description=description,
                venue_name=venue_name,
                starts_at=starts_at,
                ticket_url=link,
                source_url=link or feed_url,
                source_name=source_name,
                source_kind="rss",
                source_event_id=link or f"{source_name}:{title}:{starts_at.isoformat()}",
                source_attribution=source_name,
                raw_payload={"title": title, "link": link, "description": description},
                confidence_hints={
                    "has_source_id": bool(link),
                    "has_ticket_url": bool(link),
                    "has_artist": False,
                    "has_venue": venue_name != "Venue TBC",
                    "has_datetime": True,
                },
            )
        )
    return events


def parse_ical_events(raw: str, source_name: str, feed_url: str) -> list[NormalizedSourceEvent]:
    events: list[NormalizedSourceEvent] = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", raw, flags=re.DOTALL):
        fields = _ical_fields(block)
        title = fields.get("SUMMARY")
        start_value = fields.get("DTSTART")
        starts_at = _parse_ical_datetime(start_value or "")
        if not title or not starts_at:
            continue
        location = fields.get("LOCATION") or "Venue TBC"
        events.append(
            NormalizedSourceEvent(
                title=title,
                artist_name=title,
                description=fields.get("DESCRIPTION"),
                venue_name=location,
                starts_at=starts_at,
                ends_at=_parse_ical_datetime(fields.get("DTEND") or ""),
                ticket_url=fields.get("URL"),
                source_url=fields.get("URL") or feed_url,
                source_name=source_name,
                source_kind="ical",
                source_event_id=fields.get("UID") or f"{source_name}:{title}:{starts_at.isoformat()}",
                source_attribution=source_name,
                raw_payload=fields,
                confidence_hints={
                    "has_source_id": bool(fields.get("UID")),
                    "has_ticket_url": bool(fields.get("URL")),
                    "has_artist": False,
                    "has_venue": location != "Venue TBC",
                    "has_datetime": True,
                },
            )
        )
    return events


def _xml_text(node: ET.Element, tag: str) -> str | None:
    found = node.find(tag)
    return found.text.strip() if found is not None and found.text else None


def _atom_link(node: ET.Element) -> str | None:
    found = node.find("{http://www.w3.org/2005/Atom}link")
    return found.attrib.get("href") if found is not None else None


def _parse_feed_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parse_datetime(value)
    except Exception:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _parse_ical_datetime(value: str) -> datetime | None:
    if not value:
        return None
    clean = value.replace("Z", "+00:00")
    if re.fullmatch(r"\d{8}", clean):
        clean = f"{clean[:4]}-{clean[4:6]}-{clean[6:8]}T00:00:00+00:00"
    elif re.fullmatch(r"\d{8}T\d{6}([+-]\d{2}:\d{2})?", clean):
        clean = f"{clean[:4]}-{clean[4:6]}-{clean[6:8]}T{clean[9:11]}:{clean[11:13]}:{clean[13:15]}{clean[15:]}"
    try:
        parsed = isoparse(clean)
    except Exception:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _ical_fields(block: str) -> dict[str, str]:
    normalized = "\n".join(line.strip() for line in block.splitlines())
    unfolded = re.sub(r"\r?\n[ \t]", "", normalized)
    fields: dict[str, str] = {}
    for raw_line in unfolded.splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        key = key.split(";", 1)[0].strip().upper()
        fields[key] = value.strip().replace("\\n", "\n")
    return fields


def _extract_location(value: str) -> str | None:
    match = re.search(r"(?:venue|location):\s*([^<\n]+)", value, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None
