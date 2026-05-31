from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.services.app_settings import get_raw_setting, get_settings_payload, save_settings
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("")
def read_settings(db: Session = Depends(get_db)) -> dict:
    return get_settings_payload(db)


@router.patch("")
def patch_settings(payload: dict, db: Session = Depends(get_db)) -> dict:
    return save_settings(db, payload)


@router.post("/test-ticketmaster")
def test_ticketmaster(db: Session = Depends(get_db)) -> dict:
    adapter = TicketmasterDiscoveryAdapter(api_key=get_raw_setting(db, "ticketmaster_api_key"))
    ok, message = adapter.test_connection()
    return {"ok": ok, "source": "Ticketmaster Discovery API", "message": message}


@router.post("/test-instagram")
def test_instagram(db: Session = Depends(get_db)) -> dict:
    missing = [
        key
        for key in [
            "meta_app_id",
            "meta_app_secret",
            "facebook_page_id",
            "instagram_business_account_id",
            "meta_access_token",
        ]
        if not get_raw_setting(db, key)
    ]
    ready = not missing
    return {
        "ok": ready,
        "source": "Instagram Graph API",
        "message": "Meta credentials are configured." if ready else f"Missing: {', '.join(missing)}",
        "required_permissions": [
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "pages_read_engagement",
        ],
        "account_type": "Instagram Business or Creator account connected to a Facebook Page",
    }


@router.post("/test-all")
def test_all(db: Session = Depends(get_db)) -> dict:
    ticketmaster = test_ticketmaster(db)
    instagram = test_instagram(db)
    return {
        "ok": bool(ticketmaster["ok"] and instagram["ok"]),
        "checks": [ticketmaster, instagram],
    }
