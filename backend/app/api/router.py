from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, cities, events, health, venues

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(cities.router, prefix="/cities", tags=["cities"])
api_router.include_router(venues.router, prefix="/venues", tags=["venues"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

