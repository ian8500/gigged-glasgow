from __future__ import annotations

from app.sources.bandsintown import BandsintownAdapter
from app.sources.base import EventSourceAdapter
from app.sources.eventbrite import EventbriteAdapter
from app.sources.manual_csv import ManualCsvAdapter
from app.sources.placeholder import StaticSourceAdapter
from app.sources.skiddle import SkiddleAdapter
from app.sources.songkick import SongkickAdapter
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter
from app.sources.venue_page import PublicVenuePageAdapter


def get_default_adapters() -> list[EventSourceAdapter]:
    return [
        TicketmasterDiscoveryAdapter(),
        ManualCsvAdapter(),
        EventbriteAdapter(),
        BandsintownAdapter(),
        SkiddleAdapter(),
        SongkickAdapter(),
        PublicVenuePageAdapter(),
        StaticSourceAdapter("Gigs in Scotland", "gigs-in-scotland", "placeholder", "manual_only", "Manual/reference source until official feed/API permission is available.", "unknown", "unknown"),
        StaticSourceAdapter("What's On Glasgow", "whats-on-glasgow", "placeholder", "manual_only", "Manual/reference source until official feed/API permission is available.", "unknown", "unknown"),
        StaticSourceAdapter("See Tickets", "see-tickets", "partner", "partner_access_required", "Partner/feed access required; no scraping.", "unknown", "unknown"),
        StaticSourceAdapter("AXS", "axs", "partner", "partner_access_required", "Partner/feed access required; no scraping.", "unknown", "unknown"),
        StaticSourceAdapter("Ticketweb", "ticketweb", "partner", "partner_access_required", "Partner/feed access required; no scraping.", "unknown", "unknown"),
        StaticSourceAdapter("DICE", "dice", "partner", "partner_access_required", "No private API use or scraping. Partner permission required.", "unknown", "no"),
        StaticSourceAdapter("Resident Advisor", "resident-advisor", "partner", "partner_access_required", "No private API use or scraping. Partner permission required.", "unknown", "no"),
        StaticSourceAdapter("Ents24", "ents24", "partner", "partner_access_required", "Partner/feed access required; no scraping.", "unknown", "unknown"),
        StaticSourceAdapter("Venue websites", "venue-websites", "venue_feed", "manual_only", "Use official feeds or structured data only; no brute-force scraping.", "unknown", "conditional"),
        StaticSourceAdapter("Promoter submissions", "promoter-submissions", "manual", "manual_only", "Public submissions go to review and never publish automatically.", "no", "yes", True),
    ]
