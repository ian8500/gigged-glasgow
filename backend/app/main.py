from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.settings import settings
from app.db.schema import create_or_update_local_schema
from app.db.session import engine
from app.models import artist, city, city_brand, event, ingestion_log, source, social_post, venue, venue_check_log, venue_coverage, weekly_issue  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        description="City-based live music discovery and Instagram publishing API.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def create_local_tables() -> None:
        create_or_update_local_schema(engine)

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
