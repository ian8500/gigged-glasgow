from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cities.base import CityConfig
from app.cities.registry import get_city_config, list_city_configs
from app.models.city import City
from app.models.city_brand import CityBrand
from app.models.venue import Venue


def create_city_from_template(db: Session, template_slug: str) -> City:
    config = get_city_config(template_slug)
    city = upsert_city_config(db, config)
    db.commit()
    db.refresh(city)
    return city


def upsert_city_config(db: Session, config: CityConfig) -> City:
    city = db.scalar(select(City).where(City.slug == config.slug))
    if city is None:
        city = City(
            slug=config.slug,
            name=config.city_name,
            country=config.country,
            timezone=config.timezone,
            default_radius_km=config.radius_km,
            weekly_window_start=config.weekly_roundup_start,
            weekly_window_end=config.weekly_roundup_end,
        )
        db.add(city)
        db.flush()

    city.name = config.city_name
    city.country = config.country
    city.timezone = config.timezone
    city.default_radius_km = config.radius_km
    city.weekly_window_start = config.weekly_roundup_start
    city.weekly_window_end = config.weekly_roundup_end

    brand = db.scalar(select(CityBrand).where(CityBrand.city_id == city.id))
    if brand is None:
        brand = CityBrand(city_id=city.id)
        db.add(brand)
    brand.brand_name = config.brand_name
    brand.handle = config.handle
    brand.tagline = config.tagline
    brand.colours = config.colours.model_dump()
    brand.hashtags = config.hashtags
    brand.voice_notes = "\n".join(config.voice_notes)
    brand.default_posting_schedule = config.default_posting_schedule.model_dump()

    for venue_template in config.venues:
        venue = db.scalar(
            select(Venue).where(Venue.city_id == city.id, Venue.slug == venue_template.slug)
        )
        if venue is None:
            venue = Venue(
                city_id=city.id,
                slug=venue_template.slug,
                name=venue_template.name,
                is_whitelisted=True,
            )
            db.add(venue)
        venue.name = venue_template.name
        venue.address = venue_template.address
        venue.postcode = venue_template.postcode
        venue.capacity = venue_template.capacity
        venue.website_url = venue_template.website_url
        venue.instagram_handle = venue_template.instagram_handle
        venue.is_whitelisted = venue_template.slug in config.venue_whitelist

    return city


def city_template_payloads() -> list[dict]:
    return [config.model_dump() for config in list_city_configs()]


def city_brand_payload(city: City) -> dict:
    brand = city.brand
    return {
        "slug": city.slug,
        "city_name": city.name,
        "country": city.country,
        "timezone": city.timezone,
        "radius_km": city.default_radius_km,
        "weekly_roundup_start": city.weekly_window_start,
        "weekly_roundup_end": city.weekly_window_end,
        "brand_name": brand.brand_name if brand else f"Gigged {city.name}",
        "handle": brand.handle if brand else f"@gigged{city.slug}",
        "tagline": brand.tagline if brand else f"Your weekly {city.name} gig radar.",
        "colours": brand.colours if brand else {},
        "hashtags": brand.hashtags if brand else [],
        "voice_notes": brand.voice_notes.splitlines() if brand and brand.voice_notes else [],
        "default_posting_schedule": brand.default_posting_schedule if brand else {},
    }
