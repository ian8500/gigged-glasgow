from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.source import Source
from app.models.source_health import SourceHealth
from app.services.app_settings import get_raw_setting
from app.services.ingestion import apply_adapter_metadata, ensure_source, ingest_city
from app.services.source_health import ensure_source_health, record_source_test, source_health_payload
from app.sources.bandsintown import BandsintownAdapter
from app.sources.eventbrite import EventbriteAdapter
from app.sources.registry import get_default_adapters
from app.sources.songkick import SongkickAdapter

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
    return [source_payload(source, db.get(SourceHealth, source.id)) for source in sources]


@router.patch("/{source_id}", dependencies=[Depends(require_admin)])
def update_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.name == EventbriteAdapter.name and payload.is_enabled is True:
        adapter = EventbriteAdapter(api_key=get_raw_setting(db, "eventbrite_api_key"))
        ok, message = adapter.test_connection()
        if not ok:
            raise HTTPException(status_code=400, detail=f"Eventbrite source was not enabled: {message}")
    if source.current_mode in {"placeholder", "manual_only", "partner_access_required"} and payload.is_enabled is True:
        adapter = adapter_for_source(source, db)
        if adapter and adapter.requires_credentials:
            ok, message = adapter.test_connection()
            if not ok:
                raise HTTPException(status_code=400, detail=message)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    if source.name == EventbriteAdapter.name and source.is_enabled:
        source.base_url = EventbriteAdapter.api_base_url
        source.terms_url = source.terms_url or "https://www.eventbrite.com/help/en-us/articles/460838/eventbrite-api-terms-of-use/"
    db.commit()
    db.refresh(source)
    return source_payload(source, db.get(SourceHealth, source.id))


@router.post("/{source_id}/test", dependencies=[Depends(require_admin)])
def test_source(source_id: int, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    adapter = adapter_for_source(source, db)
    if adapter is None:
        raise HTTPException(status_code=400, detail="No adapter registered for this source.")
    ok, message = adapter.test_connection()
    configured = adapter.is_configured()
    status = "working" if ok else adapter.source_status()
    health = record_source_test(db, source, ok, message, configured=configured, status=status)
    db.commit()
    return {"ok": ok, "source": source.name, "message": message, "health": source_health_payload(source, health)}


@router.post("/{source_id}/ingest", dependencies=[Depends(require_admin)])
def ingest_source(source_id: int, city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    adapter = adapter_for_source(source, db)
    if adapter is None:
        raise HTTPException(status_code=400, detail="No adapter registered for this source.")
    report = ingest_city(db, city, adapters=[adapter])
    return {
        "city": report.city,
        "source": source.name,
        "events_found": report.fetched,
        "events_created": report.created,
        "events_updated": report.updated,
        "duplicates_skipped": report.skipped,
        "failures": report.failures,
        "warnings": report.warnings,
        "logs": report.source_logs,
    }


def ensure_default_sources(db: Session) -> None:
    for adapter in get_default_adapters():
        source = ensure_source(db, adapter.name, adapter.kind)
        apply_adapter_metadata(source, adapter)
        ensure_source_health(db, source, configured=adapter_configured_for_ui(adapter, db))
    db.commit()


def source_payload(source: Source, health: SourceHealth | None = None) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "slug": source.slug,
        "kind": source.kind,
        "base_url": source.base_url,
        "terms_url": source.terms_url,
        "is_enabled": source.is_enabled,
        "notes": source.notes,
        "requires_credentials": source.requires_credentials,
        "required_settings": [item for item in (source.required_settings or "").split(",") if item],
        "official_api_available": source.official_api_available,
        "current_mode": source.current_mode,
        "terms_reviewed": source.terms_reviewed,
        "automation_allowed": source.automation_allowed,
        "limitations": source.limitations,
        "admin_url": source.admin_url,
        "health": source_health_payload(source, health),
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }


def adapter_for_source(source: Source, db: Session):
    for adapter in get_default_adapters():
        if adapter.name != source.name:
            continue
        if adapter.name == EventbriteAdapter.name:
            return EventbriteAdapter(api_key=get_raw_setting(db, "eventbrite_api_key"))
        if adapter.name == BandsintownAdapter.name:
            return BandsintownAdapter(
                app_id=get_raw_setting(db, "bandsintown_app_id"),
                artist_seed_list=get_raw_setting(db, "bandsintown_artist_seed_list"),
            )
        if adapter.name == SongkickAdapter.name:
            return SongkickAdapter(
                api_key=get_raw_setting(db, "songkick_api_key"),
                partner_mode=str(get_raw_setting(db, "songkick_partner_mode") or "").lower() == "true",
                metro_area_id=get_raw_setting(db, "songkick_metro_area_id"),
            )
        return adapter
    return None


def adapter_configured_for_ui(adapter, db: Session) -> bool:
    configured = getattr(adapter, "is_configured", lambda: True)()
    required_settings = getattr(adapter, "required_settings", [])
    if not required_settings:
        return configured
    if "songkick_partner_mode" in required_settings:
        return (
            bool(get_raw_setting(db, "songkick_api_key"))
            and str(get_raw_setting(db, "songkick_partner_mode") or "").lower() == "true"
            and bool(get_raw_setting(db, "songkick_metro_area_id"))
        )
    return all(bool(get_raw_setting(db, key)) for key in required_settings)
