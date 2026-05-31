from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.ingestion_log import IngestionLog
from app.services.app_settings import get_raw_setting
from app.services.ingestion import ingest_city, ingestion_log_payload
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/ticketmaster")
def ingest_ticketmaster(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    if city != "glasgow":
        raise HTTPException(status_code=400, detail="Ticketmaster ingestion currently supports Glasgow.")
    adapter = TicketmasterDiscoveryAdapter(api_key=get_raw_setting(db, "ticketmaster_api_key"))
    report = ingest_city(db, city, adapters=[adapter])
    return report_payload(report)


@router.post("/all")
def ingest_all(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    report = ingest_city(db, city)
    return report_payload(report)


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


def report_payload(report) -> dict:
    return {
        "city": report.city,
        "events_found": report.fetched,
        "events_created": report.created,
        "events_updated": report.updated,
        "duplicates_skipped": report.skipped,
        "failures": report.failures,
        "warnings": report.warnings,
        "logs": report.source_logs,
    }
