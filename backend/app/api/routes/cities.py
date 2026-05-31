from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.cities.glasgow import GLASGOW_CONFIG
from app.cities.registry import list_city_configs
from app.models.city import City
from app.schemas.city import CityRead
from app.services.city_brands import city_brand_payload

router = APIRouter()


@router.get("", response_model=list[CityRead])
def list_cities(db: Session = Depends(get_db)) -> list[City]:
    return list(db.scalars(select(City).order_by(City.name)))


@router.get("/config/glasgow")
def glasgow_config() -> dict:
    return GLASGOW_CONFIG.model_dump()


@router.get("/templates")
def city_templates() -> list[dict]:
    return [config.model_dump() for config in list_city_configs()]


@router.get("/{slug}", response_model=CityRead)
def get_city(slug: str, db: Session = Depends(get_db)) -> City:
    city = db.scalar(select(City).where(City.slug == slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city


@router.get("/{slug}/brand")
def get_city_brand(slug: str, db: Session = Depends(get_db)) -> dict:
    city = db.scalar(select(City).where(City.slug == slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city_brand_payload(city)
