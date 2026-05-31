from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.source import Source
from app.services.ingestion import ensure_source
from app.sources.registry import get_default_adapters

router = APIRouter()


class SourceUpdate(BaseModel):
    is_enabled: bool | None = None
    notes: str | None = None
    base_url: str | None = None
    terms_url: str | None = None


@router.get("")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    ensure_default_sources(db)
    sources = db.scalars(select(Source).order_by(Source.name.asc()))
    return [source_payload(source) for source in sources]


@router.patch("/{source_id}", dependencies=[Depends(require_admin)])
def update_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source_payload(source)


def ensure_default_sources(db: Session) -> None:
    for adapter in get_default_adapters():
        source = ensure_source(db, adapter.name, adapter.kind)
        if adapter.name in {"Eventbrite", "Bandsintown", "Songkick"}:
            source.is_enabled = False
            source.notes = source.notes or "Placeholder source. Configure settings before enabling ingestion."
        if adapter.name == "Public venue pages":
            source.is_enabled = False
            source.notes = source.notes or "Safe framework only; live venue checks are robots-aware and manual-first."
    db.commit()


def source_payload(source: Source) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "kind": source.kind,
        "base_url": source.base_url,
        "terms_url": source.terms_url,
        "is_enabled": source.is_enabled,
        "notes": source.notes,
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }
