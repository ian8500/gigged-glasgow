from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    weekly_issue_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_issues.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), index=True)
    platform: Mapped[str] = mapped_column(String(80), default="instagram")
    template_name: Mapped[str] = mapped_column(String(120), default="weekly_roundup")
    caption: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    preview_payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    city = relationship("City")
    weekly_issue = relationship("WeeklyIssue", back_populates="social_posts")
    event = relationship("Event", back_populates="social_posts")

