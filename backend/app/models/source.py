from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    slug: Mapped[str | None] = mapped_column(String(180), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(400))
    terms_url: Mapped[str | None] = mapped_column(String(400))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    requires_credentials: Mapped[bool] = mapped_column(Boolean, default=False)
    required_settings: Mapped[str | None] = mapped_column(Text)
    official_api_available: Mapped[str | None] = mapped_column(String(40))
    current_mode: Mapped[str | None] = mapped_column(String(80))
    terms_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    automation_allowed: Mapped[str | None] = mapped_column(String(40))
    limitations: Mapped[str | None] = mapped_column(Text)
    admin_url: Mapped[str | None] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="source")
