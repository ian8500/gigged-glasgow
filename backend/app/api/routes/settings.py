from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.services.ingestion import ensure_source
from app.services.app_settings import get_raw_setting, get_settings_payload, save_settings
from app.sources.bandsintown import BandsintownAdapter
from app.sources.eventbrite import EventbriteAdapter
from app.sources.songkick import SongkickAdapter
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


@router.post("/test-eventbrite")
def test_eventbrite(db: Session = Depends(get_db)) -> dict:
    adapter = EventbriteAdapter(api_key=get_raw_setting(db, "eventbrite_api_key"))
    ok, message = adapter.test_connection()
    return {"ok": ok, "source": "Eventbrite", "message": message}


@router.post("/test-bandsintown")
def test_bandsintown(db: Session = Depends(get_db)) -> dict:
    adapter = BandsintownAdapter(
        app_id=get_raw_setting(db, "bandsintown_app_id"),
        artist_seed_list=get_raw_setting(db, "bandsintown_artist_seed_list"),
    )
    ok, message = adapter.test_connection()
    return {"ok": ok, "source": "Bandsintown", "message": message}


@router.post("/test-songkick")
def test_songkick(db: Session = Depends(get_db)) -> dict:
    adapter = SongkickAdapter(
        api_key=get_raw_setting(db, "songkick_api_key"),
        partner_mode=str(get_raw_setting(db, "songkick_partner_mode") or "").lower() == "true",
        metro_area_id=get_raw_setting(db, "songkick_metro_area_id"),
    )
    ok, message = adapter.test_connection()
    return {"ok": ok, "source": "Songkick", "message": message}


@router.post("/enable-eventbrite")
def enable_eventbrite(db: Session = Depends(get_db)) -> dict:
    adapter = EventbriteAdapter(api_key=get_raw_setting(db, "eventbrite_api_key"))
    ok, message = adapter.test_connection()
    if not ok:
        return {"ok": False, "source": "Eventbrite", "message": f"Eventbrite was not enabled: {message}"}

    source = ensure_source(db, EventbriteAdapter.name, EventbriteAdapter.kind)
    source.is_enabled = True
    source.base_url = EventbriteAdapter.api_base_url
    source.terms_url = source.terms_url or "https://www.eventbrite.com/help/en-us/articles/460838/eventbrite-api-terms-of-use/"
    source.notes = "Enabled after a successful Eventbrite profile token test."
    db.commit()
    return {"ok": True, "source": "Eventbrite", "message": "Eventbrite source enabled after token test succeeded."}


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
    eventbrite = test_eventbrite(db)
    bandsintown = test_bandsintown(db)
    songkick = test_songkick(db)
    instagram = test_instagram(db)
    return {
        "ok": bool(ticketmaster["ok"] and eventbrite["ok"] and bandsintown["ok"] and songkick["ok"] and instagram["ok"]),
        "checks": [ticketmaster, eventbrite, bandsintown, songkick, instagram],
    }
