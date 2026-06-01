from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.services.venue_scraper import (
    approve_candidate,
    candidate_payload,
    convert_candidate_to_event,
    latest_scrape_status,
    list_candidates,
    reject_candidate,
    run_city_scrape,
    scrape_venue,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/status")
def scrape_status(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    return latest_scrape_status(db, city)


@router.post("/run")
def run_scrape(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    return run_city_scrape(city, db=db)


@router.post("/venues/{venue_id}")
def scrape_single_venue(venue_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        result = scrape_venue(venue_id, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "venue_id": result.venue_id,
        "venue_name": result.venue_name,
        "status": result.status,
        "events_found": result.events_found,
        "candidates_created": result.candidates_created,
        "duplicates": result.duplicates,
        "errors": result.errors,
        "warnings": result.warnings,
    }


@router.get("/candidates")
def scrape_candidates(
    city: str = "glasgow",
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_candidates(db, city, status)


@router.post("/candidates/{candidate_id}/approve")
def approve_scrape_candidate(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return candidate_payload(approve_candidate(db, candidate_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/reject")
def reject_scrape_candidate(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return candidate_payload(reject_candidate(db, candidate_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/convert-to-event")
def convert_scrape_candidate(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        event = convert_candidate_to_event(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": event.id,
        "title": event.title,
        "starts_at": event.starts_at.isoformat(),
        "status": event.status,
        "needs_review": event.needs_review,
        "confidence_score": event.confidence_score,
        "source_url": event.source_url,
    }
