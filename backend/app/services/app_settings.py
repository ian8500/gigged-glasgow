from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from itertools import count
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.app_setting import AppSetting


@dataclass(frozen=True, slots=True)
class SettingField:
    key: str
    label: str
    section: str
    secret: bool = False
    env_name: str | None = None
    default: Any = None


SETTING_FIELDS = [
    SettingField("ticketmaster_api_key", "Ticketmaster API Key", "event_data_apis", True, "TICKETMASTER_API_KEY"),
    SettingField("eventbrite_api_key", "Eventbrite API Key", "event_data_apis", True, "EVENTBRITE_API_KEY"),
    SettingField("songkick_api_key", "Songkick API Key", "event_data_apis", True, "SONGKICK_API_KEY"),
    SettingField("songkick_partner_mode", "Songkick partner mode", "event_data_apis", False, "SONGKICK_PARTNER_MODE", "false"),
    SettingField("songkick_metro_area_id", "Songkick metro area ID", "event_data_apis", False, "SONGKICK_METRO_AREA_ID", ""),
    SettingField("bandsintown_app_id", "Bandsintown App ID/API details", "event_data_apis", True, "BANDSINTOWN_APP_ID"),
    SettingField("bandsintown_artist_seed_list", "Bandsintown artist seed list", "event_data_apis", False, "BANDSINTOWN_ARTIST_SEED_LIST", ""),
    SettingField("skiddle_source_settings", "Skiddle source settings", "event_data_apis", False, "SKIDDLE_SOURCE_SETTINGS"),
    SettingField("gigs_in_scotland_source_settings", "Gigs in Scotland source settings", "event_data_apis", False, "GIGS_IN_SCOTLAND_SOURCE_SETTINGS"),
    SettingField("whats_on_glasgow_source_settings", "What's On Glasgow source settings", "event_data_apis", False, "WHATS_ON_GLASGOW_SOURCE_SETTINGS"),
    SettingField("city_name", "City name", "glasgow_search_configuration", False, None, "Glasgow"),
    SettingField("country_code", "Country code", "glasgow_search_configuration", False, None, "GB"),
    SettingField("default_radius", "Default radius", "glasgow_search_configuration", False, None, "25"),
    SettingField("date_range_days", "Date range to search", "glasgow_search_configuration", False, None, "30"),
    SettingField("default_event_type", "Default event type", "glasgow_search_configuration", False, None, "music"),
    SettingField("include_free_events", "Include free events", "glasgow_search_configuration", False, None, "true"),
    SettingField("include_paid_events", "Include paid events", "glasgow_search_configuration", False, None, "true"),
    SettingField("minimum_confidence_score", "Minimum confidence score", "glasgow_search_configuration", False, None, "0.6"),
    SettingField("venue_whitelist", "Venue whitelist", "glasgow_search_configuration", False, None, ""),
    SettingField("venue_blacklist", "Venue blacklist", "glasgow_search_configuration", False, None, ""),
    SettingField("instagram_handle", "Instagram handle", "instagram_meta", False, "INSTAGRAM_HANDLE"),
    SettingField("meta_app_id", "Meta App ID", "instagram_meta", True, "META_APP_ID"),
    SettingField("meta_app_secret", "Meta App Secret", "instagram_meta", True, "META_APP_SECRET"),
    SettingField("facebook_page_id", "Facebook Page ID", "instagram_meta", True, "FACEBOOK_PAGE_ID"),
    SettingField("instagram_business_account_id", "Instagram Business Account ID", "instagram_meta", True, "INSTAGRAM_BUSINESS_ACCOUNT_ID"),
    SettingField("meta_access_token", "Long-lived Access Token", "instagram_meta", True, "META_ACCESS_TOKEN"),
    SettingField("default_hashtags", "Default hashtags", "instagram_meta", False, None, "#GiggedGlasgow #GlasgowGigs #GlasgowMusic"),
    SettingField("default_caption_footer", "Default caption footer", "instagram_meta", False, None, "Save this for your next Glasgow gig night."),
    SettingField("manual_posting_mode", "Manual posting mode", "instagram_meta", False, None, "true"),
    SettingField("official_api_publishing_mode", "Official API publishing mode", "instagram_meta", False, None, "placeholder_disabled"),
    SettingField("brand_name", "Brand name", "brand_settings", False, None, "Gigged Glasgow"),
    SettingField("tagline", "Tagline", "brand_settings", False, None, "Your weekly Glasgow gig radar."),
    SettingField("colour_palette", "Colour palette", "brand_settings", False, None, "#D7FF38,#1BC7B8,#F94C66,#6C4AB6"),
    SettingField("default_post_style", "Default post style", "brand_settings", False, None, "bold_editorial"),
    SettingField("logo_text", "Logo text", "brand_settings", False, None, "Gigged Glasgow"),
    SettingField("city_specific_hashtags", "City-specific hashtags", "brand_settings", False, None, "#GiggedGlasgow #GlasgowGigs #GlasgowMusic"),
]

FIELD_BY_KEY = {field.key: field for field in SETTING_FIELDS}


def get_settings_payload(db: Session) -> dict[str, Any]:
    saved = {row.key: row for row in db.scalars(select(AppSetting))}
    sections: dict[str, list[dict[str, Any]]] = {}
    flat: dict[str, Any] = {}

    for field in SETTING_FIELDS:
        value, source = resolve_setting(db, field.key, saved=saved)
        if field.secret:
            output_value = mask_secret(value)
            configured = bool(value)
        else:
            output_value = value if value is not None else ""
            configured = bool(output_value)
        item = {
            "key": field.key,
            "label": field.label,
            "section": field.section,
            "secret": field.secret,
            "configured": configured,
            "value": output_value,
            "source": source,
            "env_name": field.env_name,
        }
        sections.setdefault(field.section, []).append(item)
        flat[field.key] = output_value

    return {"sections": sections, "values": flat, "updated_at": latest_update(saved)}


def save_settings(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    for key, incoming in payload.items():
        field = FIELD_BY_KEY.get(key)
        if field is None:
            continue
        if incoming is None:
            continue
        value = str(incoming).strip()
        if field.secret and (not value or "••••" in value):
            continue
        row = db.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, is_secret=field.secret)
            db.add(row)
        row.is_secret = field.secret
        row.value = encrypt_secret(value) if field.secret else value
    db.commit()
    return get_settings_payload(db)


def get_raw_setting(db: Session, key: str) -> str | None:
    field = FIELD_BY_KEY.get(key)
    if field is None:
        return None
    value, _source = resolve_setting(db, key)
    return value


def resolve_setting(
    db: Session,
    key: str,
    saved: dict[str, AppSetting] | None = None,
) -> tuple[str | None, str]:
    field = FIELD_BY_KEY[key]
    rows = saved if saved is not None else {row.key: row for row in db.scalars(select(AppSetting))}
    row = rows.get(key)
    if row and row.value:
        return (decrypt_secret(row.value) if field.secret else row.value), "saved"

    env_attr = key
    env_value = getattr(settings, env_attr, None)
    if env_value:
        return str(env_value), "env"
    if field.default is not None:
        return str(field.default), "default"
    return None, "empty"


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return f"{value[:2]}••••{value[-2:]}"
    return f"{value[:4]}••••{value[-4:]}"


def latest_update(saved: dict[str, AppSetting]) -> str | None:
    updates = [row.updated_at for row in saved.values() if row.updated_at]
    return max(updates).isoformat() if updates else None


def encrypt_secret(value: str) -> str:
    raw = value.encode("utf-8")
    stream = _secret_stream(len(raw))
    encrypted = bytes(byte ^ key for byte, key in zip(raw, stream))
    return "local:v1:" + base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_secret(value: str) -> str:
    if not value.startswith("local:v1:"):
        return value
    raw = base64.urlsafe_b64decode(value.removeprefix("local:v1:").encode("ascii"))
    stream = _secret_stream(len(raw))
    return bytes(byte ^ key for byte, key in zip(raw, stream)).decode("utf-8")


def _secret_stream(length: int) -> bytes:
    seed = settings.admin_api_key.encode("utf-8") or b"gigged-glasgow-local"
    chunks = []
    for index in count():
        chunks.append(hashlib.sha256(seed + index.to_bytes(4, "big")).digest())
        joined = b"".join(chunks)
        if len(joined) >= length:
            return joined[:length]
    raise RuntimeError("unreachable")
