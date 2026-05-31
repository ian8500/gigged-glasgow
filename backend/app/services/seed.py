from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cities.glasgow import GLASGOW_CONFIG
from app.models.city import City
from app.models.source import Source
from app.models.venue import Venue
from app.services.city_brands import upsert_city_config
from app.services.venue_coverage import seed_glasgow_venue_coverage

SEED_DIR = Path(__file__).resolve().parents[2] / "seeds"


def seed_glasgow(db: Session) -> None:
    city = upsert_city_config(db, GLASGOW_CONFIG)
    db.flush()

    manual_source = db.scalar(select(Source).where(Source.name == "Manual admin entry"))
    if manual_source is None:
        db.add(
            Source(
                name="Manual admin entry",
                kind="manual",
                base_url=None,
                terms_url=None,
                notes="Fallback source for promoter, venue, and editor-submitted events.",
            )
        )

    venues = json.loads((SEED_DIR / "glasgow_venues.json").read_text(encoding="utf-8"))
    for item in venues:
        existing = db.scalar(
            select(Venue).where(Venue.city_id == city.id, Venue.slug == item["slug"])
        )
        if existing is not None:
            continue
        same_name = db.scalar(
            select(Venue).where(
                Venue.city_id == city.id,
                func.lower(Venue.name) == item["name"].lower(),
            )
        )
        if same_name is not None:
            continue
        db.add(Venue(city_id=city.id, is_whitelisted=True, **item))

    db.commit()
    seed_glasgow_venue_coverage(db)
