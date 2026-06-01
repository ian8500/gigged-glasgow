from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.city import City
from app.models.weekly_issue import WeeklyIssue
from app.services.social_generation import generate_social_posts
from app.services.weekly_run import run_weekly_issue_workflow

router = APIRouter(dependencies=[Depends(require_admin)])


class WeeklyIssueUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    status: str | None = None


@router.post("/run")
def weekly_run(city: str = "glasgow", db: Session = Depends(get_db)) -> dict:
    try:
        report = run_weekly_issue_workflow(db, city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "fix": "Run python manage.py seed, then retry the weekly run."}) from exc
    return {
        "city": report.city,
        "issue_id": report.issue_id,
        "issue_slug": report.issue_slug,
        "total_events_found": report.ingest.get("events_found", 0),
        "new_events_added": report.ingest.get("events_created", 0),
        "duplicates_skipped": report.ingest.get("duplicates_skipped", 0),
        "venues_checked": report.venue_coverage.get("pre_publish_report", {}).get("venues_checked", 0),
        "source_failures": report.ingest.get("failures", 0),
        "venues_needing_review": report.venue_coverage.get("summary", {}).get("venues_needing_manual_review", 0),
        "confidence_score": report.venue_coverage.get("summary", {}).get("coverage_score", 0),
        "recommended_posts_to_publish": report.posts_created,
        "ingest": report.ingest,
        "venue_coverage": report.venue_coverage,
        "dedupe": report.dedupe,
        "candidate_events": report.candidates,
        "posts_created": report.posts_created,
        "safe_to_publish": report.safe_to_publish,
    }


@router.get("/issues")
def list_issues(city: str = "glasgow", db: Session = Depends(get_db)) -> list[dict]:
    city_record = require_city(db, city)
    issues = db.scalars(
        select(WeeklyIssue)
        .where(WeeklyIssue.city_id == city_record.id)
        .order_by(WeeklyIssue.generated_at.desc().nullslast(), WeeklyIssue.created_at.desc())
    )
    return [issue_payload(issue) for issue in issues]


@router.get("/issues/{issue_id}")
def get_issue(issue_id: int, db: Session = Depends(get_db)) -> dict:
    return issue_payload(require_issue(db, issue_id))


@router.patch("/issues/{issue_id}")
def update_issue(issue_id: int, payload: WeeklyIssueUpdate, db: Session = Depends(get_db)) -> dict:
    issue = require_issue(db, issue_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, key, value)
    db.commit()
    db.refresh(issue)
    return issue_payload(issue)


@router.post("/issues/{issue_id}/generate-posts")
def generate_issue_posts(issue_id: int, db: Session = Depends(get_db)) -> dict:
    issue = require_issue(db, issue_id)
    report = generate_social_posts(db, issue.city.slug)
    return {
        "issue_id": issue.id,
        "city": issue.city.slug,
        "generated": report.generated,
        "post_ids": report.post_ids,
    }


def require_city(db: Session, city_slug: str) -> City:
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city


def require_issue(db: Session, issue_id: int) -> WeeklyIssue:
    issue = db.get(WeeklyIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Weekly issue not found")
    return issue


def issue_payload(issue: WeeklyIssue) -> dict:
    return {
        "id": issue.id,
        "city_id": issue.city_id,
        "title": issue.title,
        "slug": issue.slug,
        "starts_on": issue.starts_on.isoformat(),
        "ends_on": issue.ends_on.isoformat(),
        "status": issue.status,
        "summary": issue.summary,
        "generated_at": issue.generated_at.isoformat() if issue.generated_at else None,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }
