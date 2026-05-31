from __future__ import annotations

from app.sources.bandsintown import BandsintownAdapter
from app.sources.base import EventSourceAdapter
from app.sources.eventbrite import EventbriteAdapter
from app.sources.manual_csv import ManualCsvAdapter
from app.sources.songkick import SongkickAdapter
from app.sources.ticketmaster import TicketmasterDiscoveryAdapter
from app.sources.venue_page import PublicVenuePageAdapter


def get_default_adapters() -> list[EventSourceAdapter]:
    return [
        TicketmasterDiscoveryAdapter(),
        ManualCsvAdapter(),
        EventbriteAdapter(),
        BandsintownAdapter(),
        SongkickAdapter(),
        PublicVenuePageAdapter(),
    ]
