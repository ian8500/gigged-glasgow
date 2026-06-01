from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, cities, dashboard, events, feeds, health, ingest, scrape, settings, social, sources, submissions, venues, weekly

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(cities.router, prefix="/cities", tags=["cities"])
api_router.include_router(venues.router, prefix="/venues", tags=["venues"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(weekly.router, prefix="/weekly", tags=["weekly"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(feeds.router, prefix="/feeds", tags=["feeds"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(scrape.router, prefix="/admin/scrape", tags=["scrape"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
