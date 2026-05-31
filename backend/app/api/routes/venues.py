from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.city import City
from app.models.venue import Venue
from app.schemas.venue import VenueRead

router = APIRouter()


@router.get("", response_model=list[VenueRead])
def list_venues(city: str = "glasgow", db: Session = Depends(get_db)) -> list[Venue]:
    statement = (
        select(Venue)
        .join(City)
        .where(City.slug == city)
        .order_by(Venue.is_whitelisted.desc(), Venue.name)
    )
    return list(db.scalars(statement))

