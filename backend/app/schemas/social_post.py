from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SocialPostRead(BaseModel):
    id: int
    city_id: int
    weekly_issue_id: int | None
    event_id: int | None
    platform: str
    template_name: str
    post_type: str
    caption: str | None
    image_path: str | None
    image_url: str | None
    image_prompt: str | None
    preview_payload: dict | None
    status: str
    publish_at: datetime | None
    planned_for: datetime | None
    exported_at: datetime | None
    posted_manually_at: datetime | None
    failure_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialPostEdit(BaseModel):
    caption: str | None = None
    title: str | None = None
    description: str | None = None
    hashtags: list[str] | None = None
    status: str | None = None
