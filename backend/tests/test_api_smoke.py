from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.settings import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.app_setting import AppSetting


def test_requested_endpoint_smoke() -> None:
    with TestClient(app) as client:
        headers = {"X-Admin-Token": settings.admin_api_key}
        checks = [
            ("GET", "/api/dashboard/summary?city=glasgow"),
            ("GET", "/api/dashboard/activity?city=glasgow"),
            ("GET", "/api/venues?city=glasgow"),
            ("GET", "/api/events?city=glasgow&limit=1"),
            ("GET", "/api/ingest/logs?city=glasgow"),
            ("GET", "/api/sources"),
            ("GET", "/api/weekly/issues?city=glasgow"),
            ("GET", "/api/social/posts?city=glasgow"),
            ("GET", "/api/settings"),
        ]
        for method, path in checks:
            response = client.request(method, path, headers=headers)
            assert response.status_code in {200, 404}, path


def test_settings_save_load_masks_secret() -> None:
    with TestClient(app) as client:
        headers = {"X-Admin-Token": settings.admin_api_key}
        response = client.patch(
            "/api/settings",
            headers=headers,
            json={
                "ticketmaster_api_key": "tm-test-secret-1234",
                "city_name": "Glasgow",
                "manual_posting_mode": "true",
            },
        )
        assert response.status_code == 200
        values = response.json()["values"]
        assert values["ticketmaster_api_key"] == "tm-t••••1234"
        assert values["city_name"] == "Glasgow"

        response = client.get("/api/settings", headers=headers)
        assert response.status_code == 200
        ticketmaster = response.json()["values"]["ticketmaster_api_key"]
        assert "tm-test-secret-1234" not in ticketmaster
        assert ticketmaster.endswith("1234")

    with SessionLocal() as db:
        for key in ["ticketmaster_api_key", "city_name", "manual_posting_mode"]:
            row = db.get(AppSetting, key)
            if row is not None:
                db.delete(row)
            db.commit()
