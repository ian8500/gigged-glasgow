from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SourceHealth(Base):
    __tablename__ = "source_health"

    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(80), default="untested", nullable=False, index=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    configured: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    events_last_found: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list[str] | None] = mapped_column(JSON)

    source = relationship("Source")
