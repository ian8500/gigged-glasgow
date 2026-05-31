from __future__ import annotations

from app.cities.base import CityColours, CityConfig, CityCoordinates, PostingSchedule, VenueTemplate

EDINBURGH_CONFIG = CityConfig(
    slug="edinburgh",
    city_name="Edinburgh",
    brand_name="Gigged Edinburgh",
    handle="@giggededinburgh",
    tagline="Your weekly Edinburgh gig radar.",
    country="Scotland",
    timezone="Europe/London",
    colours=CityColours(primary="#7b4aa0", secondary="#d987a1", accent="#d6f84c"),
    venues=[
        VenueTemplate(name="Sneaky Pete's", slug="sneaky-petes", address="73 Cowgate"),
        VenueTemplate(name="The Queen's Hall", slug="the-queens-hall", address="85-89 Clerk Street"),
        VenueTemplate(name="La Belle Angele", slug="la-belle-angele", address="11 Hastie's Close"),
    ],
    coordinates=CityCoordinates(latitude=55.9533, longitude=-3.1883),
    radius_km=18,
    hashtags=["#GiggedEdinburgh", "#EdinburghGigs", "#EdinburghMusic", "#LiveMusic"],
    voice_notes=["Cultural, compact, festival-aware.", "Useful over hype.", "Respect small rooms and touring artists."],
    default_posting_schedule=PostingSchedule(weekly_roundup_day="thursday", weekly_roundup_time="17:30"),
    venue_whitelist=["sneaky-petes", "the-queens-hall", "la-belle-angele"],
    genre_filters=["alternative", "electronic", "folk", "indie", "jazz", "pop", "rock"],
)

MANCHESTER_CONFIG = CityConfig(
    slug="manchester",
    city_name="Manchester",
    brand_name="Gigged Manchester",
    handle="@giggedmanchester",
    tagline="Your weekly Manchester gig radar.",
    country="England",
    timezone="Europe/London",
    colours=CityColours(primary="#f6b33d", secondary="#28b8a7", accent="#ef4d2f"),
    venues=[
        VenueTemplate(name="YES", slug="yes", address="38 Charles Street"),
        VenueTemplate(name="Gorilla", slug="gorilla", address="54-56 Whitworth Street West"),
        VenueTemplate(name="Albert Hall", slug="albert-hall", address="27 Peter Street"),
    ],
    coordinates=CityCoordinates(latitude=53.4808, longitude=-2.2426),
    radius_km=22,
    hashtags=["#GiggedManchester", "#ManchesterGigs", "#ManchesterMusic", "#LiveMusic"],
    voice_notes=["Confident, scene-literate, direct.", "Avoid nostalgia traps.", "Useful for promoters and fans."],
    default_posting_schedule=PostingSchedule(weekly_roundup_day="thursday", weekly_roundup_time="18:00"),
    venue_whitelist=["yes", "gorilla", "albert-hall"],
    genre_filters=["alternative", "electronic", "hip-hop", "indie", "jazz", "pop", "rock"],
)

LIVERPOOL_CONFIG = CityConfig(
    slug="liverpool",
    city_name="Liverpool",
    brand_name="Gigged Liverpool",
    handle="@giggedliverpool",
    tagline="Your weekly Liverpool gig radar.",
    country="England",
    timezone="Europe/London",
    colours=CityColours(primary="#28b8a7", secondary="#d6f84c", accent="#ef4d2f"),
    venues=[
        VenueTemplate(name="The Jacaranda", slug="the-jacaranda", address="21-23 Slater Street"),
        VenueTemplate(name="Invisible Wind Factory", slug="invisible-wind-factory", address="3 Regent Road"),
        VenueTemplate(name="Camp and Furnace", slug="camp-and-furnace", address="67 Greenland Street"),
    ],
    coordinates=CityCoordinates(latitude=53.4084, longitude=-2.9916),
    radius_km=20,
    hashtags=["#GiggedLiverpool", "#LiverpoolGigs", "#LiverpoolMusic", "#LiveMusic"],
    voice_notes=["Warm, sharp and venue-first.", "Celebrate new artists without Beatles clichés.", "Clear city-guide utility."],
    default_posting_schedule=PostingSchedule(weekly_roundup_day="thursday", weekly_roundup_time="18:00"),
    venue_whitelist=["the-jacaranda", "invisible-wind-factory", "camp-and-furnace"],
    genre_filters=["alternative", "electronic", "folk", "indie", "pop", "punk", "rock"],
)
