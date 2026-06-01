from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn

from app.core.settings import settings
from app.db.session import Base


VENUE_SQLITE_COLUMNS = {
    "official_website_url": "VARCHAR(400)",
    "event_listings_url": "VARCHAR(600)",
    "ticketing_url": "VARCHAR(600)",
    "official_events_url": "VARCHAR(600)",
    "feed_url": "VARCHAR(800)",
    "selector_config": "JSON",
    "scraper_selector_config": "JSON",
    "structured_data_supported": "BOOLEAN DEFAULT 0 NOT NULL",
    "source_mode": "VARCHAR(80) DEFAULT 'manual_only' NOT NULL",
    "scraper_status": "VARCHAR(40) DEFAULT 'not_checked' NOT NULL",
    "scraper_notes": "TEXT",
    "robots_allowed": "BOOLEAN",
    "last_structured_data_check": "DATETIME",
    "last_structured_data_error": "TEXT",
    "source_discovered_from": "VARCHAR(240)",
    "last_checked_at": "DATETIME",
    "last_success_at": "DATETIME",
    "last_error": "TEXT",
    "structure_changed": "BOOLEAN DEFAULT 0 NOT NULL",
    "confidence_score": "FLOAT DEFAULT 0.5 NOT NULL",
    "last_event_found_at": "DATETIME",
    "status": "VARCHAR(40) DEFAULT 'active' NOT NULL",
    "coverage_status": "VARCHAR(40) DEFAULT 'manual_only' NOT NULL",
    "notes": "TEXT",
}

EVENT_SQLITE_COLUMNS = {
    "description": "TEXT",
    "source_url": "VARCHAR(600)",
    "venue_address": "VARCHAR(300)",
    "venue_postcode": "VARCHAR(32)",
    "latitude": "FLOAT",
    "longitude": "FLOAT",
    "duplicate_of_event_id": "INTEGER",
    "duplicate_reason": "TEXT",
    "featured": "BOOLEAN DEFAULT 0 NOT NULL",
    "instagram_suitable": "BOOLEAN DEFAULT 0 NOT NULL",
}

SOURCE_SQLITE_COLUMNS = {
    "slug": "VARCHAR(180)",
    "requires_credentials": "BOOLEAN DEFAULT 0 NOT NULL",
    "required_settings": "TEXT",
    "official_api_available": "VARCHAR(40)",
    "current_mode": "VARCHAR(80)",
    "terms_reviewed": "BOOLEAN DEFAULT 0 NOT NULL",
    "automation_allowed": "VARCHAR(40)",
    "limitations": "TEXT",
    "admin_url": "VARCHAR(400)",
}

SOCIAL_POST_SQLITE_COLUMNS = {
    "post_type": "VARCHAR(80) DEFAULT 'single_gig' NOT NULL",
    "image_path": "VARCHAR(600)",
    "image_url": "VARCHAR(600)",
    "publish_at": "DATETIME",
    "planned_for": "DATETIME",
    "exported_at": "DATETIME",
    "posted_manually_at": "DATETIME",
    "failure_reason": "TEXT",
}


def create_or_update_local_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    if not settings.database_url.startswith("sqlite"):
        return

    add_missing_sqlite_columns(engine)


def add_missing_sqlite_columns(engine: Engine) -> None:
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            existing_columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table.name})")).fetchall()
            }
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                column_sql = str(CreateColumn(column).compile(dialect=engine.dialect))
                column_sql = strip_sqlite_column_constraints(column_sql)
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column_sql}"))

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
        existing_sources = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(sources)")).fetchall()
        }
        for column_name, column_type in SOURCE_SQLITE_COLUMNS.items():
            if column_name not in existing_sources:
                connection.execute(
                    text(f"ALTER TABLE sources ADD COLUMN {column_name} {column_type}")
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


def strip_sqlite_column_constraints(column_sql: str) -> str:
    """Keep local migrations tolerant of existing rows in stale SQLite databases."""
    for token in [" NOT NULL", " PRIMARY KEY"]:
        column_sql = column_sql.replace(token, "")
    return column_sql
