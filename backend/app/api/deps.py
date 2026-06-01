from __future__ import annotations

from collections.abc import Generator

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Missing X-Admin-Token header.",
                "fix": "Send X-Admin-Token with the same ADMIN_API_KEY value used by backend/.env.",
            },
        )
    if x_admin_token != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Wrong X-Admin-Token header.",
                "fix": "Make ADMIN_API_KEY match in backend/.env and frontend/.env.local, then restart both servers.",
            },
        )
