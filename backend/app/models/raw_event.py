from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)
    ingestion_log_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_logs.id"), index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), index=True)
    duplicate_of_event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), index=True)
    city_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_event_id: Mapped[str | None] = mapped_column(String(240), index=True)
    title: Mapped[str | None] = mapped_column(String(260), index=True)
    venue_name: Mapped[str | None] = mapped_column(String(180), index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(40), default="fetched", index=True)
    review_reason: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    normalized_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    city = relationship("City")
    source = relationship("Source", back_populates="raw_events")
    ingestion_run = relationship("IngestionRun", back_populates="raw_events")
    ingestion_log = relationship("IngestionLog", back_populates="raw_events")
    event = relationship("Event", foreign_keys=[event_id], back_populates="raw_events")
    duplicate_of_event = relationship("Event", foreign_keys=[duplicate_of_event_id])
