from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.city import City
from app.models.event import Event
from app.models.social_post import SocialPost
from app.models.venue import Venue

PostFormat = Literal[
    "weekly_top_10",
    "tonight",
    "weekend_picks",
    "under_15",
    "hidden_gem",
    "new_artist_spotlight",
    "venue_spotlight",
]

EXPORT_DIR = Path(__file__).resolve().parents[2] / "exports" / "social"


@dataclass(slots=True)
class GeneratedPost:
    format: PostFormat
    title: str
    description: str
    caption: str
    hashtags: list[str]
    alt_text: str
    events: list[Event]
    venue: Venue | None = None


@dataclass(slots=True)
class SocialGenerationReport:
    city: str
    generated: int
    post_ids: list[int]


def generate_social_posts(db: Session, city_slug: str, formats: list[PostFormat] | None = None) -> SocialGenerationReport:
    city = db.scalar(select(City).where(City.slug == city_slug))
    if city is None:
        raise ValueError(f"City '{city_slug}' has not been seeded.")

    requested = formats or [
        "weekly_top_10",
        "tonight",
        "weekend_picks",
        "under_15",
        "hidden_gem",
        "new_artist_spotlight",
        "venue_spotlight",
    ]
    approved_events = get_approved_events(db, city.id)
    posts: list[SocialPost] = []

    for post_format in requested:
        generated = build_generated_post(post_format, approved_events, city.name)
        if generated is None:
            continue
        post = create_review_post(db, city, generated)
        posts.append(post)

    db.commit()
    return SocialGenerationReport(city=city_slug, generated=len(posts), post_ids=[post.id for post in posts])


def get_approved_events(db: Session, city_id: int) -> list[Event]:
    now = datetime.utcnow()
    return list(
        db.scalars(
            select(Event)
            .where(
                Event.city_id == city_id,
                Event.starts_at >= now,
                Event.status == "scheduled",
                Event.needs_review.is_(False),
            )
            .options(joinedload(Event.artist), joinedload(Event.venue), joinedload(Event.source))
            .order_by(Event.confidence_score.desc(), Event.starts_at.asc())
            .limit(40)
        )
    )


def build_generated_post(post_format: PostFormat, events: list[Event], city_name: str) -> GeneratedPost | None:
    if not events:
        return None

    if post_format == "weekly_top_10":
        selected = events[:10]
        title = "Weekly Top 10 Glasgow Gigs"
        description = "The strongest approved gigs on the radar this week."
    elif post_format == "tonight":
        today = datetime.utcnow().date()
        selected = [event for event in events if event.starts_at.date() == today][:6] or events[:3]
        title = "Tonight in Glasgow"
        description = "Last-minute picks with enough detail to make a quick call."
    elif post_format == "weekend_picks":
        selected = [event for event in events if event.starts_at.weekday() in {4, 5, 6}][:6] or events[:4]
        title = "Weekend Picks"
        description = "Friday-to-Sunday gigs worth saving."
    elif post_format == "under_15":
        selected = [
            event for event in events if event.price_min is not None and float(event.price_min) <= 15
        ][:6]
        if not selected:
            selected = events[:3]
        title = "Cheap Gigs Under £15"
        description = "Low-cost Glasgow gigs that still feel worth the night out."
    elif post_format == "hidden_gem":
        selected = sorted(
            events,
            key=lambda event: (
                bool(event.venue and event.venue.capacity and event.venue.capacity <= 300),
                bool(event.price_min is not None and float(event.price_min) <= 15),
                event.confidence_score or 0,
            ),
            reverse=True,
        )[:1]
        title = "Hidden Gem"
        description = "A smaller-room pick with enough signal to deserve attention."
    elif post_format == "new_artist_spotlight":
        selected = events[:1]
        title = "New Artist Spotlight"
        description = "One artist to check before they hit bigger rooms."
    else:
        selected = events[:1]
        title = "Venue Spotlight"
        description = "A trusted Glasgow room with a gig worth knowing."

    return GeneratedPost(
        format=post_format,
        title=title,
        description=description,
        caption=generate_caption(title, description, selected, city_name),
        hashtags=generate_hashtags(post_format, selected, city_name),
        alt_text=generate_alt_text(title, selected),
        events=selected,
        venue=selected[0].venue if selected else None,
    )


def create_review_post(
    db: Session,
    city: City,
    generated: GeneratedPost,
    weekly_issue_id: int | None = None,
) -> SocialPost:
    first_event = generated.events[0] if generated.events else None
    post = SocialPost(
        city_id=city.id,
        weekly_issue_id=weekly_issue_id,
        event_id=first_event.id if first_event and generated.format != "weekly_top_10" else None,
        platform="instagram",
        template_name=generated.format,
        post_type=post_type_for_format(generated.format),
        caption=generated.caption,
        image_prompt=generated.description,
        status="needs_review",
        planned_for=planned_publish_time(generated.format),
        publish_at=planned_publish_time(generated.format),
        preview_payload={},
    )
    db.add(post)
    db.flush()

    payload = build_preview_payload(post.id, generated)
    square_path = export_square_png(payload)
    png_paths = export_carousel_pngs(payload)
    payload["exports"] = {
        "square_png_path": str(square_path),
        "png_path": str(png_paths[0]),
        "png_paths": [str(path) for path in png_paths],
        "carousel_png_paths": [str(path) for path in png_paths],
    }
    json_path = export_scheduling_json(post.id, payload)
    payload["exports"]["json_path"] = str(json_path)
    post.preview_payload = payload
    post.image_path = str(square_path)
    return post


def create_social_draft_for_event(
    db: Session,
    event: Event,
    post_type: str = "single_gig",
    publish_at: datetime | None = None,
) -> SocialPost:
    venue = event.venue.name if event.venue else "Venue TBC"
    artist = event.artist.name if event.artist else event.title
    caption = (
        f"{artist} at {venue}\n"
        f"{event.starts_at:%a %-d %b, %H:%M}\n\n"
        "Save this for your next Glasgow gig night.\n\n"
        "#GiggedGlasgow #GlasgowGigs #GlasgowMusic"
    )
    post = SocialPost(
        city_id=event.city_id,
        event_id=event.id,
        platform="instagram",
        template_name=post_type,
        post_type=post_type,
        caption=caption,
        image_url=event.image_url,
        status="draft",
        publish_at=publish_at,
        planned_for=publish_at,
        preview_payload={
            "title": event.title,
            "description": event.editorial_note,
            "hashtags": ["#GiggedGlasgow", "#GlasgowGigs", "#GlasgowMusic"],
            "alt_text": f"Gig listing for {event.title} at {venue}.",
        },
    )
    db.add(post)
    db.flush()
    return post


def post_type_for_format(post_format: str) -> str:
    return {
        "weekly_top_10": "weekend_roundup",
        "weekend_picks": "weekend_roundup",
        "cheap_gigs": "cheap_gigs",
        "hidden_gem": "single_gig",
    }.get(post_format, "single_gig")


def regenerate_post(db: Session, post: SocialPost) -> SocialPost:
    city = db.get(City, post.city_id)
    if city is None:
        raise ValueError("Post city no longer exists.")
    events = get_approved_events(db, city.id)
    generated = build_generated_post(normalize_post_format(post.template_name), events, city.name)
    if generated is None:
        raise ValueError("No approved events available to regenerate this post.")

    payload = build_preview_payload(post.id, generated)
    square_path = export_square_png(payload)
    png_paths = export_carousel_pngs(payload)
    payload["exports"] = {
        "square_png_path": str(square_path),
        "png_path": str(png_paths[0]),
        "png_paths": [str(path) for path in png_paths],
        "carousel_png_paths": [str(path) for path in png_paths],
    }
    json_path = export_scheduling_json(post.id, payload)
    payload["exports"]["json_path"] = str(json_path)
    post.caption = generated.caption
    post.image_prompt = generated.description
    post.preview_payload = payload
    post.planned_for = planned_publish_time(generated.format)
    post.status = "needs_review"
    db.commit()
    db.refresh(post)
    return post


def normalize_post_format(value: str) -> PostFormat:
    valid: set[str] = {
        "weekly_top_10",
        "tonight",
        "weekend_picks",
        "under_15",
        "new_artist_spotlight",
        "venue_spotlight",
        "hidden_gem",
    }
    return value if value in valid else "weekly_top_10"  # type: ignore[return-value]


def build_preview_payload(post_id: int, generated: GeneratedPost) -> dict:
    event_payload = [event_to_payload(event) for event in generated.events]
    return {
        "post_id": post_id,
        "brand": "Gigged Glasgow",
        "platform": "instagram",
        "format": generated.format,
        "title": generated.title,
        "description": generated.description,
        "caption": generated.caption,
        "hashtags": generated.hashtags,
        "alt_text": generated.alt_text,
        "status": "needs_review",
        "publishing": {"auto_publish": False},
        "events": event_payload,
        "carousel_slides": build_carousel_slides(generated, event_payload),
        "internal_source_attribution": [
            {
                "event_id": event.id,
                "source_attribution": event.source_attribution,
            }
            for event in generated.events
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def build_carousel_slides(generated: GeneratedPost, event_payload: list[dict]) -> list[dict]:
    if generated.format not in {"weekly_top_10", "weekend_picks"}:
        return [
            {
                "slide": 1,
                "kind": "single",
                "title": generated.title,
                "description": generated.description,
                "events": event_payload,
            }
        ]

    if generated.format == "weekend_picks":
        slides = [
            {
                "slide": 1,
                "kind": "cover",
                "title": "Weekend Picks",
                "description": "Friday-to-Sunday gigs worth saving.",
            }
        ]
        for index, event in enumerate(event_payload, start=2):
            slides.append(
                {
                    "slide": index,
                    "kind": "event",
                    "title": event["artist"],
                    "description": event["short_description"],
                    "event": event,
                }
            )
        return slides

    slides = [
        {
            "slide": 1,
            "kind": "cover",
            "title": "Weekly Top 10 Glasgow Gigs",
            "description": "Save this before the weekend fills up.",
        }
    ]
    for index, event in enumerate(event_payload, start=2):
        slides.append(
            {
                "slide": index,
                "kind": "event",
                "title": event["artist"],
                "description": event["short_description"],
                "event": event,
            }
        )
    return slides


def event_to_payload(event: Event) -> dict:
    return {
        "event_title": event.title,
        "artist": event.artist.name if event.artist else event.title,
        "venue": event.venue.name if event.venue else "Venue TBC",
        "date": event.starts_at.date().isoformat(),
        "door_time": event.starts_at.strftime("%H:%M") if event.starts_at else None,
        "ticket_price": format_price(event),
        "ticket_link": event.ticket_url,
        "genre": event.genre,
        "source_attribution": event.source_attribution,
        "short_description": punchy_description(event),
    }


def generate_caption(title: str, description: str, events: list[Event], city_name: str) -> str:
    lines = [f"{title}.", description, ""]
    for event in events[:10]:
        venue = event.venue.name if event.venue else "Venue TBC"
        artist = event.artist.name if event.artist else event.title
        lines.append(f"{event.starts_at:%a %-d %b} · {artist} at {venue} · {format_price(event)}")
    lines.extend(["", "Save it, send it, check ticket links before you go."])
    return "\n".join(lines)


def generate_hashtags(post_format: PostFormat, events: list[Event], city_name: str) -> list[str]:
    tags = ["#GiggedGlasgow", "#GlasgowGigs", "#GlasgowMusic", "#LiveMusic"]
    if post_format == "under_15":
        tags.extend(["#CheapGigs", "#Under15"])
    if post_format == "hidden_gem":
        tags.extend(["#HiddenGem", "#IndependentVenue"])
    if post_format == "tonight":
        tags.append("#TonightInGlasgow")
    if post_format == "venue_spotlight" and events and events[0].venue:
        tags.append(f"#{compact_tag(events[0].venue.name)}")
    for event in events[:3]:
        if event.genre:
            tags.append(f"#{compact_tag(event.genre)}")
    return list(dict.fromkeys(tags))[:14]


def generate_alt_text(title: str, events: list[Event]) -> str:
    event_bits = [
        f"{event.artist.name if event.artist else event.title} at {event.venue.name if event.venue else 'Venue TBC'} on {event.starts_at:%A %-d %B}"
        for event in events[:5]
    ]
    return f"Instagram graphic for Gigged Glasgow titled {title}, listing: {'; '.join(event_bits)}."


def export_carousel_pngs(payload: dict) -> list[Path]:
    slides = payload.get("carousel_slides") or [
        {
            "slide": 1,
            "title": payload["title"],
            "description": payload["description"],
            "events": payload["events"],
        }
    ]
    return [export_png(payload, slide, width=1080, height=1350, suffix=f"slide-{slide['slide']}") for slide in slides]


def export_pngs(payload: dict) -> list[Path]:
    return export_carousel_pngs(payload)


def export_square_png(payload: dict) -> Path:
    slide = {
        "slide": "square",
        "title": payload["title"],
        "description": payload["description"],
        "events": payload["events"],
    }
    return export_png(payload, slide, width=1080, height=1080, suffix="square")


def export_png(
    payload: dict,
    slide: dict,
    width: int = 1080,
    height: int = 1350,
    suffix: str | None = None,
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = suffix or f"slide-{slide['slide']}"
    path = EXPORT_DIR / f"post-{payload['post_id']}-{payload['format']}-{suffix}.png"
    image = Image.new("RGB", (width, height), "#f3efe4")
    draw = ImageDraw.Draw(image)
    title_font = safe_font(72 if height == 1080 else 82)
    body_font = safe_font(30 if height == 1080 else 34)
    small_font = safe_font(24)

    draw.rectangle((48, 48, width - 48, height - 48), outline="#0e0e10", width=12)
    draw.rectangle((74, 74, 370, 128), fill="#d6f84c")
    draw.text((92, 88), "GIGGED GLASGOW", fill="#0e0e10", font=small_font)
    draw.text((86, 190), wrap_text(slide["title"], 18), fill="#0e0e10", font=title_font, spacing=6)
    description_y = 450 if height == 1080 else 510
    draw.text((86, description_y), wrap_text(slide["description"], 40), fill="#393642", font=body_font, spacing=8)

    y = 600 if height == 1080 else 700
    slide_events = [slide["event"]] if slide.get("event") else slide.get("events", payload["events"])[:5]
    for event in slide_events:
        if y > height - 230:
            break
        draw.line((86, y - 22, width - 86, y - 22), fill="#0e0e10", width=5)
        line = f"{event['date']} · {event['artist']} · {event['venue']} · {event['ticket_price']}"
        draw.text((86, y), wrap_text(line, 42), fill="#0e0e10", font=body_font, spacing=4)
        y += 106 if height == 1080 else 116

    badge_y = height - 182
    draw.rectangle((width - 350, badge_y, width - 86, badge_y + 70), fill="#ef4d2f")
    draw.text((width - 326, badge_y + 20), "REVIEW DRAFT", fill="#fff8e8", font=small_font)
    draw.text((86, height - 140), "@giggedglasgow", fill="#0e0e10", font=small_font)
    image.save(path)
    return path


def export_scheduling_json(post_id: int, payload: dict) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"post-{post_id}-{payload['format']}.json"
    schedule_payload = {
        "id": post_id,
        "platform": "instagram",
        "status": payload.get("status", "needs_review"),
        "auto_publish": False,
        "publishing_mode": "manual_export",
        "caption": payload["caption"],
        "hashtags": payload["hashtags"],
        "alt_text": payload["alt_text"],
        "media": {
            "square_png_path": payload.get("exports", {}).get("square_png_path"),
            "png_path": payload.get("exports", {}).get("png_path"),
        },
        "media_items": payload.get("exports", {}).get("png_paths", []),
        "carousel_media_items": payload.get("exports", {}).get("carousel_png_paths", []),
        "events": payload["events"],
        "carousel_slides": payload.get("carousel_slides", []),
        "manual_posting_checklist": [
            "Download or locate exported PNG files.",
            "Copy caption and hashtags.",
            "Review alt text for accessibility.",
            "Post manually in Instagram or an approved scheduling tool.",
        ],
    }
    path.write_text(json.dumps(schedule_payload, indent=2), encoding="utf-8")
    return path


def export_post_assets(post: SocialPost) -> dict:
    payload = dict(post.preview_payload or {})
    if not payload:
        raise ValueError("Post has no preview payload to export.")
    square_path = export_square_png(payload)
    png_paths = export_carousel_pngs(payload)
    payload["exports"] = {
        "square_png_path": str(square_path),
        "png_path": str(png_paths[0]),
        "png_paths": [str(path) for path in png_paths],
        "carousel_png_paths": [str(path) for path in png_paths],
    }
    json_path = export_scheduling_json(post.id, payload)
    payload["exports"]["json_path"] = str(json_path)
    post.preview_payload = payload
    return payload["exports"]


def planned_publish_time(post_format: str, now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    offsets = {
        "weekly_top_10": (0, 18),
        "weekend_picks": (3, 11),
        "under_15": (1, 18),
        "hidden_gem": (2, 18),
        "tonight": (0, 12),
        "new_artist_spotlight": (4, 12),
        "venue_spotlight": (5, 12),
    }
    days, hour = offsets.get(post_format, (0, 18))
    planned = now + timedelta(days=days)
    return planned.replace(hour=hour, minute=0, second=0, microsecond=0)


def format_price(event: Event) -> str:
    if event.price_min is None:
        return "Price TBC"
    if event.price_max and event.price_max != event.price_min:
        return f"£{event.price_min}–£{event.price_max}"
    return f"£{event.price_min}"


def punchy_description(event: Event) -> str:
    artist = event.artist.name if event.artist else event.title
    venue = event.venue.name if event.venue else "a Glasgow venue"
    genre = f" {event.genre}" if event.genre else ""
    return f"{artist} brings{genre} energy to {venue}. Worth checking before tickets move."


def compact_tag(value: str) -> str:
    return "".join(part.capitalize() for part in value.replace("&", " ").replace("-", " ").split())


def wrap_text(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width))


def safe_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue
    return ImageFont.load_default()
