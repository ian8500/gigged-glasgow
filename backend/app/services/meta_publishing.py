from __future__ import annotations

from dataclasses import dataclass

from app.core.settings import settings
from app.models.social_post import SocialPost


@dataclass(slots=True)
class MetaPublishReadiness:
    ready: bool
    reason: str
    required_permissions: list[str]
    account_type: str


REQUIRED_PERMISSIONS = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
]


def get_meta_readiness() -> MetaPublishReadiness:
    missing = []
    if not settings.meta_app_id:
        missing.append("META_APP_ID")
    if not settings.meta_app_secret:
        missing.append("META_APP_SECRET")
    if not settings.meta_access_token:
        missing.append("META_ACCESS_TOKEN")
    if not settings.instagram_business_account_id:
        missing.append("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    if missing:
        return MetaPublishReadiness(
            ready=False,
            reason=f"Missing environment variables: {', '.join(missing)}",
            required_permissions=REQUIRED_PERMISSIONS,
            account_type="Instagram Business or Creator account connected to a Facebook Page",
        )

    if not settings.meta_publishing_enabled:
        return MetaPublishReadiness(
            ready=False,
            reason="META_PUBLISHING_ENABLED is false; manual export mode is active.",
            required_permissions=REQUIRED_PERMISSIONS,
            account_type="Instagram Business or Creator account connected to a Facebook Page",
        )

    return MetaPublishReadiness(
        ready=True,
        reason="Credentials are configured and publishing flag is enabled.",
        required_permissions=REQUIRED_PERMISSIONS,
        account_type="Instagram Business or Creator account connected to a Facebook Page",
    )


def prepare_meta_publish_payload(post: SocialPost) -> dict:
    payload = post.preview_payload or {}
    exports = payload.get("exports", {})
    return {
        "graph_api_version": settings.meta_graph_api_version,
        "instagram_business_account_id": settings.instagram_business_account_id,
        "caption": post.caption,
        "media_type": "IMAGE" if len(exports.get("png_paths", [])) <= 1 else "CAROUSEL",
        "local_media_paths": exports.get("png_paths") or [exports.get("png_path")],
        "note": "Placeholder only. Official publishing later requires hosted media URLs and Meta Graph API media container creation/publish calls.",
    }


def publish_via_meta_placeholder(post: SocialPost) -> dict:
    readiness = get_meta_readiness()
    if not readiness.ready:
        return {
            "published": False,
            "status": "manual_export_ready",
            "reason": readiness.reason,
            "fallback": "Use exported PNG paths and caption for manual Instagram posting.",
            "payload": prepare_meta_publish_payload(post),
        }
    return {
        "published": False,
        "status": "placeholder_only",
        "reason": "Meta publishing service is intentionally not active in v1.",
        "payload": prepare_meta_publish_payload(post),
    }
