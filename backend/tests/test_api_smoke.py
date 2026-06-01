from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.settings import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.app_setting import AppSetting
from app.services.ingestion import IngestionReport


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
                "eventbrite_api_key": "eb-test-secret-5678",
                "city_name": "Glasgow",
                "manual_posting_mode": "true",
            },
        )
        assert response.status_code == 200
        values = response.json()["values"]
        assert values["ticketmaster_api_key"] == "tm-t••••1234"
        assert values["eventbrite_api_key"] == "eb-t••••5678"
        assert values["city_name"] == "Glasgow"

        response = client.get("/api/settings", headers=headers)
        assert response.status_code == 200
        ticketmaster = response.json()["values"]["ticketmaster_api_key"]
        eventbrite = response.json()["values"]["eventbrite_api_key"]
        assert "tm-test-secret-1234" not in ticketmaster
        assert "eb-test-secret-5678" not in eventbrite
        assert ticketmaster.endswith("1234")
        assert eventbrite.endswith("5678")

    with SessionLocal() as db:
        for key in ["ticketmaster_api_key", "eventbrite_api_key", "city_name", "manual_posting_mode"]:
            row = db.get(AppSetting, key)
            if row is not None:
                db.delete(row)
            db.commit()


def test_core_v1_smoke_endpoints(monkeypatch) -> None:
    def fake_ingest_city(db, city_slug: str) -> IngestionReport:
        return IngestionReport(city=city_slug, warnings=["Smoke test skipped external API adapters."])

    monkeypatch.setattr("app.services.weekly_run.ingest_city", fake_ingest_city)

    with TestClient(app) as client:
        headers = {"X-Admin-Token": settings.admin_api_key}

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        response = client.post("/api/v1/admin/seed/glasgow", headers=headers)
        assert response.status_code == 200

        response = client.get("/api/v1/settings", headers=headers)
        assert response.status_code == 200
        assert "values" in response.json()

        response = client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"eventbrite_api_key": "eb-smoke-test-key"},
        )
        assert response.status_code == 200
        assert response.json()["values"]["eventbrite_api_key"].endswith("key")

        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        response = client.get("/api/v1/venues?city=glasgow")
        assert response.status_code == 200
        assert len(response.json()) > 0

        response = client.get("/api/v1/admin/venue-coverage?city=glasgow", headers=headers)
        assert response.status_code == 200
        assert response.json()["setup"]["venue_coverage_seeded"] is True

        response = client.post("/api/v1/admin/venue-coverage/seed/glasgow", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "seeded"

        response = client.post("/api/v1/admin/venue-coverage/check-all?city=glasgow", headers=headers)
        assert response.status_code == 200
        assert "check_results" in response.json()

        response = client.get("/api/v1/events?city=glasgow")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        response = client.post("/api/v1/weekly/run?city=glasgow", headers=headers)
        assert response.status_code == 200
        assert response.json()["city"] == "glasgow"

    with SessionLocal() as db:
        row = db.get(AppSetting, "eventbrite_api_key")
        if row is not None:
            db.delete(row)
            db.commit()


def test_admin_auth_errors_are_explained() -> None:
    with TestClient(app) as client:
        missing = client.get("/api/v1/settings")
        assert missing.status_code == 401
        assert "Missing X-Admin-Token" in missing.text

        wrong = client.get("/api/v1/settings", headers={"X-Admin-Token": "wrong"})
        assert wrong.status_code == 401
        assert "Wrong X-Admin-Token" in wrong.text
