from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models.city import City
from app.models.event import Event
from app.schemas.event import EventRead

router = APIRouter()


@router.get("", response_model=list[EventRead])
def list_events(
    city: str = "glasgow",
    upcoming_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[Event]:
    statement = (
        select(Event)
        .join(City)
        .options(joinedload(Event.venue), joinedload(Event.artist), joinedload(Event.source))
        .where(City.slug == city)
        .order_by(Event.starts_at.asc())
        .limit(min(limit, 100))
    )
    if upcoming_only:
        statement = statement.where(Event.starts_at >= datetime.now(timezone.utc))
    return list(db.scalars(statement))

