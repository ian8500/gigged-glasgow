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
    caption: str | None
    image_prompt: str | None
    preview_payload: dict | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialPostEdit(BaseModel):
    caption: str | None = None
    title: str | None = None
    description: str | None = None
    hashtags: list[str] | None = None
    status: str | None = None

