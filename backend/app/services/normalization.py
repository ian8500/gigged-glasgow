from __future__ import annotations

import re
from datetime import datetime, timezone

from slugify import slugify

from app.sources.base import NormalizedSourceEvent


def event_fingerprint(city_slug: str, event: NormalizedSourceEvent | object) -> str:
    artist = getattr(event, "artist_name", None) or getattr(event, "title")
    venue = getattr(event, "venue_name", None) or _related_name(getattr(event, "venue", None)) or "venue-tbc"
    starts_at = getattr(event, "starts_at")
    return fingerprint_parts(city_slug=city_slug, artist_name=artist, venue_name=venue, starts_at=starts_at)


def fingerprint_parts(city_slug: str, artist_name: str, venue_name: str, starts_at: datetime) -> str:
    starts_at = ensure_aware(starts_at)
    date_key = starts_at.date().isoformat()
    return slugify(f"{city_slug} {clean_name(artist_name)} {clean_name(venue_name)} {date_key}")


def clean_name(value: str) -> str:
    value = value.replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", value.strip().lower())


def event_slug(title: str, starts_at: datetime) -> str:
    return slugify(f"{title} {ensure_aware(starts_at).date().isoformat()}")


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def confidence_score(event: NormalizedSourceEvent, venue_is_whitelisted: bool) -> float:
    score = 0.35
    hints = event.confidence_hints
    score += 0.15 if hints.get("has_source_id") else 0
    score += 0.15 if hints.get("has_datetime") else 0
    score += 0.1 if hints.get("has_artist") else 0
    score += 0.1 if hints.get("has_venue") else 0
    score += 0.05 if hints.get("has_ticket_url") else 0
    score += 0.1 if venue_is_whitelisted else 0
    return min(round(score, 2), 1.0)


def needs_review(score: float, venue_is_whitelisted: bool) -> bool:
    return score < 0.75 or not venue_is_whitelisted


def _related_name(value: object | None) -> str | None:
    return getattr(value, "name", None) if value is not None else None
