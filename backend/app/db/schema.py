from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.settings import settings
from app.db.session import Base


VENUE_SQLITE_COLUMNS = {
    "event_listings_url": "VARCHAR(600)",
    "ticketing_url": "VARCHAR(600)",
    "source_discovered_from": "VARCHAR(240)",
    "last_checked_at": "DATETIME",
    "last_event_found_at": "DATETIME",
    "status": "VARCHAR(40) DEFAULT 'active' NOT NULL",
    "coverage_status": "VARCHAR(40) DEFAULT 'manual_only' NOT NULL",
    "notes": "TEXT",
}

EVENT_SQLITE_COLUMNS = {
    "source_url": "VARCHAR(600)",
}

SOCIAL_POST_SQLITE_COLUMNS = {
    "planned_for": "DATETIME",
    "exported_at": "DATETIME",
    "posted_manually_at": "DATETIME",
}


def create_or_update_local_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        existing = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(venues)")).fetchall()
        }
        for column_name, column_type in VENUE_SQLITE_COLUMNS.items():
            if column_name not in existing:
                connection.execute(
                    text(f"ALTER TABLE venues ADD COLUMN {column_name} {column_type}")
                )
        existing_events = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(events)")).fetchall()
        }
        for column_name, column_type in EVENT_SQLITE_COLUMNS.items():
            if column_name not in existing_events:
                connection.execute(
                    text(f"ALTER TABLE events ADD COLUMN {column_name} {column_type}")
                )
        existing_social_posts = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(social_posts)")).fetchall()
        }
        for column_name, column_type in SOCIAL_POST_SQLITE_COLUMNS.items():
            if column_name not in existing_social_posts:
                connection.execute(
                    text(f"ALTER TABLE social_posts ADD COLUMN {column_name} {column_type}")
                )
