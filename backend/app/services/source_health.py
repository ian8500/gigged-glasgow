from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.source import Source
from app.models.source_health import SourceHealth
from app.sources.base import SourceAdapterBase, SourceFetchResult


def ensure_source_health(db: Session, source: Source, configured: bool | None = None) -> SourceHealth:
    health = db.get(SourceHealth, source.id)
    if health is None:
        health = SourceHealth(source_id=source.id)
        db.add(health)
        db.flush()
    health.enabled = bool(source.is_enabled)
    if configured is not None:
        health.configured = configured
    return health


def record_source_test(
    db: Session,
    source: Source,
    ok: bool,
    message: str,
    configured: bool,
    status: str | None = None,
) -> SourceHealth:
    health = ensure_source_health(db, source, configured=configured)
    now = datetime.utcnow()
    health.last_tested_at = now
    health.enabled = bool(source.is_enabled)
    health.configured = configured
    health.status = status or ("working" if ok else "failing")
    health.last_error = None if ok else message
    health.warnings = [] if ok else [message]
    if ok:
        health.last_success_at = now
    db.flush()
    return health


def record_source_ingest(
    db: Session,
    source: Source,
    result: SourceFetchResult | None,
    configured: bool,
    failures: int,
    warnings: list[str],
    events_found: int,
) -> SourceHealth:
    health = ensure_source_health(db, source, configured=configured)
    now = datetime.utcnow()
    health.last_ingest_at = now
    health.enabled = bool(source.is_enabled)
    health.configured = configured
    health.events_last_found = events_found
    health.warnings = warnings
    health.last_error = "; ".join(result.failures if result else warnings) if failures else None
    if not source.is_enabled:
        health.status = "configured_disabled" if configured else "api_key_missing"
    elif failures:
        health.status = "failing"
    elif not configured and source.requires_credentials:
        health.status = "api_key_missing"
    else:
        health.status = "working"
        health.last_success_at = now
    db.flush()
    return health


def source_health_payload(source: Source, health: SourceHealth | None = None) -> dict[str, Any]:
    return {
        "status": health.status if health else "untested",
        "last_tested_at": health.last_tested_at.isoformat() if health and health.last_tested_at else None,
        "last_success_at": health.last_success_at.isoformat() if health and health.last_success_at else None,
        "last_ingest_at": health.last_ingest_at.isoformat() if health and health.last_ingest_at else None,
        "last_error": health.last_error if health else None,
        "configured": bool(health.configured) if health else False,
        "enabled": bool(source.is_enabled),
        "events_last_found": health.events_last_found if health else 0,
        "warnings": health.warnings if health and health.warnings else [],
    }


def adapter_metadata(adapter: SourceAdapterBase) -> dict[str, Any]:
    return {
        "slug": getattr(adapter, "slug", None),
        "requires_credentials": bool(getattr(adapter, "requires_credentials", False)),
        "required_settings": ",".join(getattr(adapter, "required_settings", [])),
        "official_api_available": getattr(adapter, "official_api_available", "unknown"),
        "current_mode": getattr(adapter, "current_mode", "placeholder"),
        "terms_reviewed": bool(getattr(adapter, "terms_reviewed", False)),
        "automation_allowed": getattr(adapter, "automation_allowed", "unknown"),
        "limitations": adapter.source_notes() if hasattr(adapter, "source_notes") else "",
        "base_url": getattr(adapter, "base_url", None),
        "terms_url": getattr(adapter, "terms_url", None),
    }
