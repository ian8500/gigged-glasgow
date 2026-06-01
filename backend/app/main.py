from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.core.settings import settings
from app.db.schema import create_or_update_local_schema
from app.db.session import engine
from app.models import app_setting, artist, city, city_brand, event, extracted_event_candidate, ingestion_log, promoter_submission, scrape_run, source, source_feed, source_health, social_post, venue, venue_check_log, venue_coverage, weekly_issue  # noqa: F401


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
    app.include_router(api_router, prefix="/api")

    @app.exception_handler(OperationalError)
    async def sqlite_operational_error_handler(_request, exc: OperationalError) -> JSONResponse:
        message = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "message": "Database schema is missing a required local table or column.",
                    "error": message,
                    "fix": "Run: cd backend && python manage.py init-db. If the local database is badly stale, run: python manage.py reset-local --yes.",
                }
            },
        )
    return app


app = create_app()
