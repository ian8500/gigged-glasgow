#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
EXPECTED_API_BASE = "http://localhost:8000/api/v1"


@dataclass
class Result:
    status: str
    label: str
    detail: str
    fix: str | None = None


def main() -> int:
    results: list[Result] = []

    backend_env_path = BACKEND_ROOT / ".env"
    frontend_env_path = FRONTEND_ROOT / ".env.local"
    backend_env = parse_env(backend_env_path)
    frontend_env = parse_env(frontend_env_path)

    add(results, backend_env_path.exists(), "backend/.env exists", str(backend_env_path), "Create backend/.env from .env.example.")
    add(results, frontend_env_path.exists(), "frontend/.env.local exists", str(frontend_env_path), "Create frontend/.env.local with NEXT_PUBLIC_API_BASE_URL and ADMIN_API_KEY.")

    backend_admin = backend_env.get("ADMIN_API_KEY")
    frontend_admin = frontend_env.get("ADMIN_API_KEY")
    add(results, bool(backend_admin), "ADMIN_API_KEY exists in backend/.env", "Set" if backend_admin else "Missing", "Add ADMIN_API_KEY=local-dev-key to backend/.env.")
    add(results, bool(frontend_admin), "ADMIN_API_KEY exists in frontend/.env.local", "Set" if frontend_admin else "Missing", "Add ADMIN_API_KEY=local-dev-key to frontend/.env.local.")
    add(
        results,
        bool(backend_admin and frontend_admin and backend_admin == frontend_admin),
        "Admin keys match",
        "backend and frontend ADMIN_API_KEY values match" if backend_admin == frontend_admin else "backend and frontend ADMIN_API_KEY values differ",
        "Set the same ADMIN_API_KEY in backend/.env and frontend/.env.local.",
    )

    api_base = frontend_env.get("NEXT_PUBLIC_API_BASE_URL")
    add(
        results,
        api_base == EXPECTED_API_BASE,
        "NEXT_PUBLIC_API_BASE_URL points to local API",
        api_base or "Missing",
        f"Set NEXT_PUBLIC_API_BASE_URL={EXPECTED_API_BASE} in frontend/.env.local.",
    )

    add(results, backend_dependencies_installed(), "Backend dependencies are installed", "FastAPI, SQLAlchemy, pytest import locally", "Run: cd backend && source .venv/bin/activate && pip install -e '.[dev]'")
    add(results, frontend_dependencies_installed(), "Frontend dependencies are installed", "frontend/node_modules and Next are present", "Run: cd frontend && npm install")

    db_url = backend_env.get("DATABASE_URL", "sqlite:///./gigged_glasgow.db")
    db_path = sqlite_path(db_url)
    schema_ready = False
    if db_path is None:
        add(results, False, "SQLite database exists or can be created", db_url, "Set DATABASE_URL to sqlite:///./gigged_glasgow.db for local development.")
    else:
        try:
            initialise_backend()
            from app.db.schema import create_or_update_local_schema
            from app.db.session import engine

            create_or_update_local_schema(engine)
            schema_ready = True
            add(results, db_path.exists(), "SQLite database exists or can be created", str(db_path), "Run: cd backend && python manage.py init-db")
        except Exception as exc:  # pragma: no cover - diagnostic output path
            add(results, False, "SQLite database exists or can be created", exc.__class__.__name__, "Run: cd backend && python manage.py init-db")

    if schema_ready and db_path is not None:
        required_tables = required_database_tables()
        existing_tables = existing_database_tables(db_path)
        missing_tables = sorted(required_tables - existing_tables)
        add(
            results,
            not missing_tables,
            "All required database tables exist",
            f"{len(required_tables) - len(missing_tables)}/{len(required_tables)} tables present",
            "Run: cd backend && python manage.py init-db" if missing_tables else None,
        )
        if not missing_tables:
            check_seed_data(results)
        else:
            results.append(Result("FIX", "Missing database tables", ", ".join(missing_tables), "Run: cd backend && python manage.py init-db"))
    else:
        for label in ["Glasgow city is seeded", "Glasgow venues are seeded", "Venue coverage data is seeded"]:
            results.append(Result("FAIL", label, "Skipped because database/schema check failed", "Run: cd backend && python manage.py init-db && python manage.py seed"))

    check_backend_health(results)
    check_frontend_reachability(results)

    print_results(results)
    return 1 if any(result.status == "FAIL" for result in results) else 0


def parse_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def add(results: list[Result], ok: bool, label: str, detail: str, fix: str | None = None) -> None:
    results.append(Result("PASS" if ok else "FAIL", label, detail, None if ok else fix))


def backend_dependencies_installed() -> bool:
    return all(importlib.util.find_spec(name) is not None for name in ["fastapi", "sqlalchemy", "pytest", "uvicorn"])


def frontend_dependencies_installed() -> bool:
    return (FRONTEND_ROOT / "node_modules" / "next").exists()


def sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    raw = database_url.removeprefix("sqlite:///")
    path = Path(raw)
    return path if path.is_absolute() else BACKEND_ROOT / path


def initialise_backend() -> None:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    os.chdir(BACKEND_ROOT)
    import app.models.app_setting  # noqa: F401
    import app.models.artist  # noqa: F401
    import app.models.city  # noqa: F401
    import app.models.city_brand  # noqa: F401
    import app.models.event  # noqa: F401
    import app.models.ingestion_log  # noqa: F401
    import app.models.promoter_submission  # noqa: F401
    import app.models.social_post  # noqa: F401
    import app.models.source  # noqa: F401
    import app.models.source_feed  # noqa: F401
    import app.models.source_health  # noqa: F401
    import app.models.venue  # noqa: F401
    import app.models.venue_check_log  # noqa: F401
    import app.models.venue_coverage  # noqa: F401
    import app.models.weekly_issue  # noqa: F401


def required_database_tables() -> set[str]:
    initialise_backend()
    from app.db.session import Base

    return set(Base.metadata.tables)


def existing_database_tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def check_seed_data(results: list[Result]) -> None:
    initialise_backend()
    from sqlalchemy import func, select

    from app.db.session import SessionLocal
    from app.models.city import City
    from app.models.venue import Venue
    from app.models.venue_coverage import VenueCoverage

    with SessionLocal() as db:
        city = db.scalar(select(City).where(City.slug == "glasgow"))
        add(results, city is not None, "Glasgow city is seeded", "Found" if city else "Missing", "Run: cd backend && python manage.py seed")
        if city is None:
            results.append(Result("FAIL", "Glasgow venues are seeded", "City missing", "Run: cd backend && python manage.py seed"))
            results.append(Result("FAIL", "Venue coverage data is seeded", "City missing", "Run: cd backend && python manage.py seed"))
            return

        venue_count = db.scalar(select(func.count(Venue.id)).where(Venue.city_id == city.id)) or 0
        coverage_count = (
            db.scalar(
                select(func.count(VenueCoverage.id))
                .join(Venue)
                .where(Venue.city_id == city.id)
            )
            or 0
        )
        add(results, venue_count > 0, "Glasgow venues are seeded", f"{venue_count} venues", "Run: cd backend && python manage.py seed")
        add(results, coverage_count > 0, "Venue coverage data is seeded", f"{coverage_count} coverage rows", "Run: cd backend && python manage.py seed")


def check_backend_health(results: list[Result]) -> None:
    try:
        initialise_backend()
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            response = client.get("/api/v1/health")
        add(results, response.status_code == 200, "Backend health endpoint works", f"in-process HTTP {response.status_code}", "Run: cd backend && python manage.py init-db")
    except Exception as exc:  # pragma: no cover - diagnostic output path
        add(results, False, "Backend health endpoint works", exc.__class__.__name__, "Run: cd backend && uvicorn app.main:app --reload")


def check_frontend_reachability(results: list[Result]) -> None:
    for url in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        try:
            with urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    results.append(Result("PASS", "Frontend local server is reachable if running", f"{url} returned HTTP {response.status}"))
                    return
        except URLError:
            continue
        except TimeoutError:
            continue
    results.append(Result("FIX", "Frontend local server is reachable if running", "No frontend server detected on localhost:3000", "Run: cd frontend && npm run dev"))


def print_results(results: list[Result]) -> None:
    width = max(len(result.label) for result in results)
    print("Gigged Glasgow local doctor")
    print("=" * 34)
    for result in results:
        print(f"{result.status:<4} {result.label:<{width}} {result.detail}")
        if result.fix:
            print(f"FIX  {'':<{width}} {result.fix}")


if __name__ == "__main__":
    raise SystemExit(main())
