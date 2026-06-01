from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.ingestion_log import IngestionLog
from app.models.source import Source
from app.models.source_health import SourceHealth
from app.services.app_settings import get_raw_setting
from app.services.ingestion import ingest_city, ingestion_log_payload
from app.sources.bandsintown import BandsintownAdapter
from app.sources.eventbrite import EventbriteAdapter
from app.sources.songkick import SongkickAdapter
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/ticketmaster")
def ingest_ticketmaster(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    if city != "glasgow":
        raise HTTPException(status_code=400, detail="Ticketmaster ingestion currently supports Glasgow.")
    adapter = TicketmasterDiscoveryAdapter(api_key=get_raw_setting(db, "ticketmaster_api_key"))
    report = ingest_city(db, city, adapters=[adapter])
    return report_payload(report, db)


@router.post("/eventbrite")
def ingest_eventbrite(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    if city != "glasgow":
        raise HTTPException(status_code=400, detail="Eventbrite ingestion currently supports Glasgow.")
    adapter = EventbriteAdapter(api_key=get_raw_setting(db, "eventbrite_api_key"))
    report = ingest_city(db, city, adapters=[adapter])
    return report_payload(report, db)


@router.post("/bandsintown")
def ingest_bandsintown(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    if city != "glasgow":
        raise HTTPException(status_code=400, detail="Bandsintown ingestion currently supports Glasgow.")
    adapter = BandsintownAdapter(
        app_id=get_raw_setting(db, "bandsintown_app_id"),
        artist_seed_list=get_raw_setting(db, "bandsintown_artist_seed_list"),
    )
    report = ingest_city(db, city, adapters=[adapter])
    return report_payload(report, db)


@router.post("/songkick")
def ingest_songkick(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    if city != "glasgow":
        raise HTTPException(status_code=400, detail="Songkick ingestion currently supports Glasgow.")
    adapter = SongkickAdapter(
        api_key=get_raw_setting(db, "songkick_api_key"),
        partner_mode=str(get_raw_setting(db, "songkick_partner_mode") or "").lower() == "true",
        metro_area_id=get_raw_setting(db, "songkick_metro_area_id"),
    )
    report = ingest_city(db, city, adapters=[adapter])
    return report_payload(report, db)


@router.post("/all")
def ingest_all(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    report = ingest_city(db, city)
    return report_payload(report, db)


@router.get("/logs")
def ingest_logs(
    city: str = "glasgow",
    source_name: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(IngestionLog).where(IngestionLog.city_slug == city)
    if source_name:
        statement = statement.where(IngestionLog.source_name == source_name)
    statement = statement.order_by(IngestionLog.started_at.desc()).limit(min(limit, 200))
    return [ingestion_log_payload(log) for log in db.scalars(statement)]


def report_payload(report, db: Session | None = None) -> dict:
    source_reports = []
    for log in report.source_logs:
        source = db.scalar(select(Source).where(Source.name == log["source_name"])) if db else None
        health = db.get(SourceHealth, source.id) if db and source else None
        source_reports.append(
            {
                "source_name": log["source_name"],
                "configured": health.configured if health else None,
                "enabled": source.is_enabled if source else None,
                "status": health.status if health else ("failing" if log["failures"] else "working"),
                "fetched": log["events_found"],
                "created": log["events_created"],
                "updated": log["events_updated"],
                "skipped": log["duplicates_skipped"],
                "duplicates": log["duplicates_skipped"],
                "errors": log["failures"],
                "warnings": log["warnings"],
            }
        )
    return {
        "city": report.city,
        "events_found": report.fetched,
        "events_created": report.created,
        "events_updated": report.updated,
        "duplicates_skipped": report.skipped,
        "failures": report.failures,
        "warnings": report.warnings,
        "logs": report.source_logs,
        "sources": source_reports,
    }
