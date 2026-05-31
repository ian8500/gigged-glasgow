from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.city import City
from app.models.social_post import SocialPost
from app.schemas.social_post import SocialPostEdit, SocialPostRead
from app.services.social_generation import export_post_assets, regenerate_post

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/posts", response_model=list[SocialPostRead])
def list_posts(city: str = "glasgow", status: str | None = None, db: Session = Depends(get_db)) -> list[SocialPost]:
    city_record = require_city(db, city)
    statement = (
        select(SocialPost)
        .where(SocialPost.city_id == city_record.id)
        .order_by(SocialPost.created_at.desc())
    )
    if status:
        statement = statement.where(SocialPost.status == status)
    return list(db.scalars(statement))


@router.post("/posts", response_model=SocialPostRead)
def create_post(payload: dict, db: Session = Depends(get_db)) -> SocialPost:
    city = require_city(db, payload.get("city", "glasgow"))
    post = SocialPost(
        city_id=city.id,
        weekly_issue_id=payload.get("weekly_issue_id"),
        event_id=payload.get("event_id"),
        platform=payload.get("platform") or "instagram",
        template_name=payload.get("template_name") or "manual",
        caption=payload.get("caption"),
        image_prompt=payload.get("image_prompt"),
        preview_payload=payload.get("preview_payload") or {},
        status=payload.get("status") or "draft",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.patch("/posts/{post_id}", response_model=SocialPostRead)
def update_post(post_id: int, payload: SocialPostEdit, db: Session = Depends(get_db)) -> SocialPost:
    post = require_post(db, post_id)
    preview = dict(post.preview_payload or {})
    if payload.caption is not None:
        post.caption = payload.caption
        preview["caption"] = payload.caption
    if payload.title is not None:
        preview["title"] = payload.title
    if payload.description is not None:
        post.image_prompt = payload.description
        preview["description"] = payload.description
    if payload.hashtags is not None:
        preview["hashtags"] = payload.hashtags
    if payload.status is not None:
        post.status = payload.status
        preview["status"] = payload.status
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


@router.post("/posts/{post_id}/approve", response_model=SocialPostRead)
def approve_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    return set_status(db, post_id, "approved")


@router.post("/posts/{post_id}/reject", response_model=SocialPostRead)
def reject_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    return set_status(db, post_id, "rejected")


@router.post("/posts/{post_id}/regenerate", response_model=SocialPostRead)
def regenerate_social_post(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    post = require_post(db, post_id)
    try:
        return regenerate_post(db, post)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/posts/{post_id}/export")
def export_post(post_id: int, db: Session = Depends(get_db)) -> dict:
    post = require_post(db, post_id)
    exports = export_post_assets(post)
    post.status = "exported"
    post.exported_at = datetime.utcnow()
    preview = dict(post.preview_payload or {})
    preview["status"] = "exported"
    preview["exports"] = exports
    post.preview_payload = preview
    db.commit()
    return {"post_id": post.id, "status": post.status, "exports": exports, "auto_publish": False}


@router.post("/posts/{post_id}/mark-posted", response_model=SocialPostRead)
def mark_posted(post_id: int, db: Session = Depends(get_db)) -> SocialPost:
    post = require_post(db, post_id)
    post.status = "posted_manually"
    post.posted_manually_at = datetime.utcnow()
    preview = dict(post.preview_payload or {})
    preview["status"] = "posted_manually"
    preview["posted_manually_at"] = post.posted_manually_at.isoformat()
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


def set_status(db: Session, post_id: int, status: str) -> SocialPost:
    post = require_post(db, post_id)
    post.status = status
    preview = dict(post.preview_payload or {})
    preview["status"] = status
    post.preview_payload = preview
    db.commit()
    db.refresh(post)
    return post


def require_post(db: Session, post_id: int) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Social post not found")
    return post


def require_city(db: Session, city_slug: str) -> City:
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city
