# Gigged Glasgow

Gigged Glasgow is a city-based live music discovery and Instagram publishing tool.
The first city is Glasgow, with the structure designed so Manchester, Edinburgh,
Liverpool, and other cities can be added by introducing new city config modules,
seed data, and source settings.

**Brand:** Gigged Glasgow  
**Tagline:** Your weekly Glasgow gig radar.  
**Stack:** FastAPI, SQLite, SQLAlchemy, Next.js, Tailwind CSS

## Source Policy

Gigged Glasgow must not bypass paywalls, logins, robots.txt, or website terms.
Event collection should prioritise official APIs, RSS feeds, permitted public
venue pages, promoter submissions, and manual admin entry. Scraping adapters
should only be added after reviewing each source's robots.txt and terms.

The venue coverage system follows the same rule. It can store venue leads from
public directories and ticketing platforms, but it treats those as discovery
signals rather than permission to scrape. Live venue checks use lightweight
robots-aware public page checks only; no browser automation, login flow,
CAPTCHA bypass, anti-bot bypass, or paywalled source access is allowed.

Instagram publishing is manual by default. The app exports PNGs, captions,
hashtags, alt text, and scheduling JSON for human review. Do not add password
login automation, private Instagram APIs, browser bots, likes, follows,
comments, or DM automation. Any future direct publishing must use Meta's
official Instagram Graph API and only after explicit approval.

## Current Phase

The MVP now has the backend pieces needed for an automated weekly gig discovery
and Instagram content engine:

- Ticketmaster Discovery API ingestion for Glasgow music events using the official API.
- A `SourceAdapter` contract for future official API, RSS, partner export, or manually supplied sources.
- Event normalisation, source attribution, source URLs, external IDs, confidence scoring, dedupe fingerprints, and ingestion logs.
- A Glasgow venue coverage dashboard with source health, stale checks, broken sources, manual-only venues, and weekly pre-publish safety reporting.
- A `Weekly Run` workflow that runs ingestion, venue coverage, dedupe, event scoring, candidate selection, and review-queue generation.
- Instagram review drafts for Weekly Top 10, Weekend Picks, Cheap Gigs Under £15, and Hidden Gem.
- Exportable `1080x1080` square PNGs, `1080x1350` carousel PNGs, captions, hashtags, alt text, and scheduling JSON.
- Manual fallback remains intact: manual event entry and CSV import are still supported.

## Project Structure

```text
.
├── .env.example
├── .gitignore
├── README.md
├── backend
│   ├── alembic.ini
│   ├── alembic
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   ├── router.py
│   │   │   └── routes
│   │   │       ├── __init__.py
│   │   │       ├── admin.py
│   │   │       ├── cities.py
│   │   │       ├── events.py
│   │   │       ├── health.py
│   │   │       └── venues.py
│   │   ├── cities
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── glasgow.py
│   │   ├── core
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   ├── crud
│   │   │   └── __init__.py
│   │   ├── db
│   │   │   ├── __init__.py
│   │   │   ├── schema.py
│   │   │   └── session.py
│   │   ├── models
│   │   │   ├── __init__.py
│   │   │   ├── artist.py
│   │   │   ├── city.py
│   │   │   ├── city_brand.py
│   │   │   ├── event.py
│   │   │   ├── social_post.py
│   │   │   ├── source.py
│   │   │   ├── venue.py
│   │   │   ├── venue_check_log.py
│   │   │   └── weekly_issue.py
│   │   ├── schemas
│   │   │   ├── __init__.py
│   │   │   ├── city.py
│   │   │   ├── event.py
│   │   │   └── venue.py
│   │   ├── services
│   │   │   ├── __init__.py
│   │   │   ├── city_brands.py
│   │   │   ├── deduplication.py
│   │   │   ├── ingestion.py
│   │   │   ├── meta_publishing.py
│   │   │   ├── normalization.py
│   │   │   ├── seed.py
│   │   │   ├── social_generation.py
│   │   │   ├── venue_coverage.py
│   │   │   └── weekly.py
│   │   └── sources
│   │       ├── __init__.py
│   │       ├── bandsintown.py
│   │       ├── base.py
│   │       ├── manual_csv.py
│   │       ├── registry.py
│   │       ├── songkick.py
│   │       ├── ticketmaster.py
│   │       └── venue_page.py
│   ├── manage.py
│   ├── pyproject.toml
│   ├── seeds
│   │   ├── glasgow_venue_coverage.json
│   │   ├── glasgow_venues.json
│   │   └── manual_events.csv
│   └── tests
│       └── test_ingestion_helpers.py
└── frontend
    ├── app
    │   ├── admin
    │   │   └── page.tsx
    │   ├── events
    │   │   └── page.tsx
    │   ├── brand
    │   │   └── page.tsx
    │   ├── venues
    │   │   └── page.tsx
    │   ├── globals.css
    │   ├── layout.tsx
    │   └── page.tsx
    ├── components
    │   ├── admin
    │   │   ├── AdminDashboard.tsx
    │   │   ├── PostPreview.tsx
    │   │   └── StatCard.tsx
    │   ├── brand
    │   │   ├── BrandSystem.tsx
    │   │   └── LogoMark.tsx
    │   ├── events
    │   │   └── EventList.tsx
    │   ├── layout
    │   │   └── Shell.tsx
    │   ├── social
    │   │   ├── SocialPostPreview.tsx
    │   │   └── SocialTemplateGrid.tsx
    │   └── venues
    │       └── VenueGrid.tsx
    ├── lib
    │   ├── api.ts
    │   ├── brand.ts
    │   └── types.ts
    ├── next-env.d.ts
    ├── next.config.mjs
    ├── package-lock.json
    ├── package.json
    ├── postcss.config.mjs
    ├── tailwind.config.ts
    └── tsconfig.json
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env
python manage.py init-db
python manage.py seed
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000/api/v1`.

Set API keys in `backend/.env`:

```dotenv
ADMIN_API_KEY=change-me-in-production
TICKETMASTER_API_KEY=your-ticketmaster-discovery-api-key
EVENTBRITE_API_KEY=
SONGKICK_API_KEY=
BANDSINTOWN_APP_ID=
MANUAL_EVENTS_CSV_PATH=seeds/manual_events.csv
INSTAGRAM_HANDLE=@giggedglasgow
META_APP_ID=
META_APP_SECRET=
FACEBOOK_PAGE_ID=
INSTAGRAM_BUSINESS_ACCOUNT_ID=
META_ACCESS_TOKEN=
```

You can also enter keys and publishing details in the frontend Settings screen
at `/settings` or `/admin/settings`. Saved secrets are stored server-side and
are only returned to the frontend as masked values such as `tm-t••••1234`.
Runtime lookup uses the saved Settings value first and `backend/.env` second.
`TICKETMASTER_API_KEY` is optional for local smoke tests, but Ticketmaster
ingestion will be skipped until it is set. Get a key from Ticketmaster
Developer and use the official Discovery API product.

Useful endpoints:

- `GET /api/v1/health`
- `GET /api/v1/dashboard/summary?city=glasgow`
- `GET /api/v1/dashboard/activity?city=glasgow`
- `GET /api/v1/cities`
- `GET /api/v1/cities/config/glasgow`
- `GET /api/v1/venues?city=glasgow`
- `POST /api/v1/venues` with `X-Admin-Token`
- `GET /api/v1/venues/{venue_id}`
- `PATCH /api/v1/venues/{venue_id}` with `X-Admin-Token`
- `DELETE /api/v1/venues/{venue_id}` with `X-Admin-Token`
- `POST /api/v1/venues/{venue_id}/check` with `X-Admin-Token`
- `POST /api/v1/venues/bulk-check?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/events?city=glasgow`
- `POST /api/v1/events` with `X-Admin-Token`
- `GET /api/v1/events/{event_id}`
- `PATCH /api/v1/events/{event_id}` with `X-Admin-Token`
- `DELETE /api/v1/events/{event_id}` with `X-Admin-Token`
- `POST /api/v1/events/{event_id}/approve` with `X-Admin-Token`
- `POST /api/v1/events/{event_id}/reject` with `X-Admin-Token`
- `POST /api/v1/events/{event_id}/mark-top-pick` with `X-Admin-Token`
- `POST /api/v1/events/dedupe?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/ingest/ticketmaster?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/ingest/all?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/ingest/logs?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/sources`
- `PATCH /api/v1/sources/{source_id}` with `X-Admin-Token`
- `POST /api/v1/weekly/run?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/weekly/issues?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/weekly/issues/{issue_id}` with `X-Admin-Token`
- `PATCH /api/v1/weekly/issues/{issue_id}` with `X-Admin-Token`
- `POST /api/v1/weekly/issues/{issue_id}/generate-posts` with `X-Admin-Token`
- `GET /api/v1/social/posts?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/social/posts` with `X-Admin-Token`
- `PATCH /api/v1/social/posts/{post_id}` with `X-Admin-Token`
- `POST /api/v1/social/posts/{post_id}/approve` with `X-Admin-Token`
- `POST /api/v1/social/posts/{post_id}/reject` with `X-Admin-Token`
- `POST /api/v1/social/posts/{post_id}/regenerate` with `X-Admin-Token`
- `POST /api/v1/social/posts/{post_id}/export` with `X-Admin-Token`
- `POST /api/v1/social/posts/{post_id}/mark-posted` with `X-Admin-Token`
- `GET /api/v1/settings` with `X-Admin-Token`
- `PATCH /api/v1/settings` with `X-Admin-Token`
- `POST /api/v1/settings/test-ticketmaster` with `X-Admin-Token`
- `POST /api/v1/settings/test-instagram` with `X-Admin-Token`
- `POST /api/v1/settings/test-all` with `X-Admin-Token`
- `GET /api/v1/admin/dashboard` with `X-Admin-Token`
- `POST /api/v1/admin/seed/glasgow` with `X-Admin-Token`
- `GET /api/v1/admin/venue-coverage?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/admin/venue-coverage/seed/glasgow` with `X-Admin-Token`
- `POST /api/v1/admin/venue-coverage/check-all?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/admin/venues/{venue_id}/check-now` with `X-Admin-Token`
- `POST /api/v1/admin/ingest/ticketmaster?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/admin/ingest/logs?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/admin/weekly-run?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/admin/weekly-run/run?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/admin/social/review-queue?city=glasgow&status=needs_review` with `X-Admin-Token`
- `GET /api/v1/admin/social/calendar?city=glasgow` with `X-Admin-Token`
- `GET /api/v1/admin/social/media-library?city=glasgow` with `X-Admin-Token`
- `POST /api/v1/admin/social/{post_id}/export` with `X-Admin-Token`
- `POST /api/v1/admin/social/{post_id}/posted-manually` with `X-Admin-Token`
- `GET /api/v1/admin/social/{post_id}/copy/caption` with `X-Admin-Token`
- `GET /api/v1/admin/social/{post_id}/copy/hashtags` with `X-Admin-Token`
- `GET /api/v1/admin/social/{post_id}/copy/alt-text` with `X-Admin-Token`

Ingestion commands:

```bash
python manage.py ingest --city glasgow
python manage.py dedupe --city glasgow
python manage.py generate-weekly --city glasgow
python manage.py generate-social --city glasgow
python manage.py weekly-run --city glasgow
```

`ingest` runs all registered source adapters. Ticketmaster uses the official
Discovery API when `TICKETMASTER_API_KEY` is configured. Manual CSV import reads
`MANUAL_EVENTS_CSV_PATH`, which defaults to `seeds/manual_events.csv` when
running from `backend`. Eventbrite, Bandsintown, Songkick, and public venue pages are
explicit placeholders until official credentials, robots.txt, and terms checks
are completed.

`weekly-run` is the preferred weekly operator command. It runs all enabled
source adapters, updates venue coverage, deduplicates events, scores the next
seven days of events, selects recommended candidates, generates Instagram review
drafts, and exports local assets. It never publishes automatically.

Ticketmaster adapter reference: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/

Venue coverage:

- `backend/seeds/glasgow_venue_coverage.json` stores the starting Glasgow venue database, including major venues, smaller rooms, outdoor concert sites, official websites, listing URLs, ticketing URLs, Instagram handles, coverage status, and notes.
- `backend/app/services/venue_coverage.py` calculates the Glasgow coverage score, exposes discovery-source metadata, checks individual venues, records check logs, detects stale checks, and explains what is missing.
- `Venue` stores `event_listings_url`, `ticketing_url`, `source_discovered_from`, `last_checked_at`, `last_event_found_at`, `status`, `coverage_status`, and `notes`.
- `VenueCheckLog` stores each check result with confidence, event count, robots-check state, structure-change flag, and diagnostic message.
- Batch coverage preflight is fast and source-aware. Individual `Check now` actions perform live robots-aware public page checks for one venue at a time.
- Before `python manage.py generate-weekly --city glasgow` creates the issue, it runs venue coverage checks, records a coverage report, flags gaps, then builds the weekly gig list.

Coverage source leads include Visit Glasgow, What's On Glasgow, Skiddle, Gigs in
Scotland, Gig Guide, Eventbrite, Ticketmaster, official venue websites, promoter
sites, and manual CSV. These are discovery inputs, not a licence to scrape.
Prefer official APIs, RSS feeds, structured data, venue-provided pages, partner
exports, and manual review.

Social generation:

- `POST /api/v1/admin/social/generate?city=glasgow` creates review drafts for all supported Instagram formats.
- `GET /api/v1/admin/social/review-queue?city=glasgow&status=needs_review` lists posts awaiting review.
- `PATCH /api/v1/admin/social/{post_id}` edits title, description, caption, hashtags, or status.
- `POST /api/v1/admin/social/{post_id}/approve` marks a draft approved.
- `POST /api/v1/admin/social/{post_id}/reject` marks a draft rejected.
- `POST /api/v1/admin/social/{post_id}/regenerate` rebuilds a draft from approved events.
- `POST /api/v1/admin/social/{post_id}/export` regenerates local PNG and JSON export assets and marks the post `exported`.
- `POST /api/v1/admin/social/{post_id}/posted-manually` marks the post as posted by a human operator.
- `GET /api/v1/admin/social/calendar?city=glasgow` returns planned posts for the next week.
- `GET /api/v1/admin/social/media-library?city=glasgow` returns generated graphics and metadata.
- Copy helpers return UI-ready strings for `Copy caption`, `Copy hashtags`, and `Copy alt text` buttons.

Supported post formats are Weekly Top 10 Glasgow Gigs, Weekend Picks, Cheap
Gigs Under £15, Hidden Gem, Tonight in Glasgow, New Artist Spotlight, and Venue
Spotlight. Generation writes square PNGs, carousel PNGs, and scheduling JSON
exports to `backend/exports/social/`. Those exports are local artifacts and are
intentionally gitignored. Nothing is published automatically.

Social post statuses are:

- `draft`
- `needs_review`
- `approved`
- `exported`
- `posted_manually`
- `rejected`

Instagram publishing preparation:

- `/admin/instagram` shows Meta/Instagram account readiness, required environment variables, required permissions, and manual posting status.
- `POST /api/v1/admin/social/{post_id}/schedule` marks an approved post as locally scheduled without publishing.
- `GET /api/v1/admin/instagram/settings` reports whether official Meta Graph API publishing could be enabled later.
- `POST /api/v1/admin/social/{post_id}/meta-placeholder` returns the prepared official-API payload shape, but deliberately does not publish in v1.

Official publishing must use Meta's Instagram Graph API only. Do not use browser
automation, password-login bots, private APIs, or Instagram scraping. To publish
through the official API later, you need an Instagram Business or Creator account
connected to a Facebook Page, a Meta app, a valid long-lived access token, and
permissions such as `instagram_basic`, `instagram_content_publish`,
`pages_show_list`, and `pages_read_engagement`. Meta publishing also requires
media to be available through public URLs for media-container creation; local PNG
paths are for manual export and approved scheduling tools only.

Official Meta references:

- https://developers.facebook.com/docs/instagram-api/
- https://developers.facebook.com/docs/instagram-api/guides/content-publishing/
- https://developers.facebook.com/docs/permissions/

The safe fallback is the default: export PNGs plus captions, hashtags, alt text,
and scheduling JSON from `backend/exports/social/`, then post manually or upload
to an approved scheduler.

Admin dashboard pages:

- `/admin` is the overview for counts, venues, social drafts, and brand previews.
- `/admin/events-inbox` is the full event intake desk with manual event and CSV upload forms.
- `/admin/needs-review` shows uncertain events that need editorial approval.
- `/admin/approved-events` shows publish-ready events.
- `/admin/venue-coverage` shows the Glasgow Venue Coverage score, source health, missing coverage work, duplicate/stale checks, and per-venue Check now controls.
- `/admin/weekly` builds the weekly issue and previews the Instagram carousel direction.
- `/admin/social` generates and reviews Instagram drafts.
- `/admin/instagram` prepares account settings for official Meta publishing and manual export fallback.
- `/admin/settings` stores API keys, source details, search defaults, Meta publishing details, and brand defaults.
- `/admin/brand-settings` shows the brand system inside the admin area.
- `/admin/city-settings` shows Glasgow settings and the later-city selector model.
- `/admin/source-settings` shows configured and placeholder ingestion sources.

Admin event operations include approve, reject, edit details, merge duplicates,
mark top pick, mark sponsored, add manual event, and upload CSV. Social operations
include generate drafts, preview carousel-style layouts, export PNG/JSON files,
edit captions, approve, reject, and regenerate. Publishing remains manual.

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```

The dashboard will be available at `http://localhost:3000`.
The Settings screen is available at `http://localhost:3000/settings`.

Frontend environment:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ADMIN_API_KEY=change-me-in-production
```

Run backend and frontend together in separate terminals:

```bash
# Terminal 1
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2
cd frontend
npm run dev
```

Verification:

```bash
npm run typecheck
npm run test:buttons
```

`npm run test:buttons` is a lightweight frontend smoke test that fails on
placeholder links, console-only interactions, and raw buttons that are not owned
by a form or explicit click handler.

## Automation Boundaries And Limitations

Automated now:

- Ticketmaster Discovery API ingestion for Glasgow music events.
- Manual event entry and CSV import.
- Venue coverage seeding, per-venue checks, bulk checks, broken/manual-only status tracking, and coverage scoring.
- Weekly Run orchestration: enabled source ingest, venue coverage, dedupe, scoring, issue creation, and draft social post generation.
- Local Instagram export assets, captions, hashtags, alt text, scheduling JSON, copy buttons, and manual posted status.

Manual-only or intentionally disabled:

- Eventbrite, Songkick, Bandsintown, Skiddle, Gigs in Scotland, and What's On Glasgow ingestion are settings-ready but not implemented as live adapters.
- Venue websites are checked only through safe public, robots-aware page checks. No login, paywall, CAPTCHA, anti-bot bypass, private API, or Instagram scraping is allowed.
- Instagram publishing is manual by default. Official Meta API publishing is prepared at the settings/readiness level but not enabled for automatic posting.

Known limitations:

- Coverage cannot guarantee every gig on the internet; the dashboard reports tracked, automated, manual-only, stale, broken, and missing-source venues so gaps are visible.
- Ticketmaster coverage depends on the official API and configured date range.
- Local SQLite secret storage is development-oriented and should be replaced with managed secret storage before production deployment.

## File Guide

### Root

- `.env.example` documents the required backend and frontend environment variables.
- `.gitignore` keeps local secrets, Python caches, SQLite files, and Next.js build output out of git.
- `README.md` is this setup, architecture, and file explanation guide.

### Backend

- `backend/pyproject.toml` declares Python dependencies and development tooling.
- `backend/manage.py` provides local management commands for creating tables and seeding Glasgow data.
- `backend/alembic.ini` configures Alembic migrations.
- `backend/alembic/env.py` loads SQLAlchemy metadata and environment settings for migrations.
- `backend/alembic/script.py.mako` is Alembic's migration file template.
- `backend/app/main.py` creates the FastAPI app, configures CORS, creates local SQLite tables on startup, and mounts API routes.
- `backend/app/core/settings.py` centralises environment-driven settings.
- `backend/app/db/schema.py` creates local tables and adds missing SQLite columns for development databases that predate new models.
- `backend/app/db/session.py` creates the SQLAlchemy engine, session factory, and declarative base.
- `backend/app/api/deps.py` defines reusable FastAPI dependencies for database sessions and admin-token protection.
- `backend/app/api/router.py` registers all route modules under `/api/v1`.
- `backend/app/api/routes/health.py` exposes a service health endpoint.
- `backend/app/api/routes/cities.py` exposes city records, brand metadata, and reusable city templates.
- `backend/app/api/routes/venues.py` lists seeded or managed venues by city.
- `backend/app/api/routes/events.py` lists upcoming events by city.
- `backend/app/api/routes/admin.py` exposes protected dashboard, seed, venue creation, and event creation endpoints.
- `backend/app/api/routes/admin.py` also exposes event moderation, duplicate merge, CSV import, ingestion logs, Weekly Run, social review, export, copy, calendar, and media-library endpoints.
- `backend/app/cities/base.py` defines the reusable city brand template schema.
- `backend/app/cities/glasgow.py` contains the first live brand template: Gigged Glasgow.
- `backend/app/cities/examples.py` contains example templates for Gigged Edinburgh, Gigged Manchester, and Gigged Liverpool.
- `backend/app/cities/registry.py` registers available city templates.
- `backend/app/models/city.py` defines city records and relationships to venues, events, and issues.
- `backend/app/models/city_brand.py` stores per-city brand metadata such as handle, tagline, colours, hashtags, voice notes, and posting schedule.
- `backend/app/models/venue.py` defines venue records, whitelisting, coverage status, event listing URLs, ticketing URLs, contact URLs, location fields, and capacity.
- `backend/app/models/venue_check_log.py` stores individual venue audit results and confidence scores.
- `backend/app/models/venue_coverage.py` stores current source-level venue coverage health.
- `backend/app/models/artist.py` defines artists that can be linked to events.
- `backend/app/models/source.py` defines source metadata for APIs, feeds, venue pages, and manual entry.
- `backend/app/models/ingestion_log.py` stores per-source ingestion run counts, failures, and warnings.
- `backend/app/models/event.py` defines normalised event records, ticket metadata, confidence, source attribution, and review status.
- `backend/app/models/weekly_issue.py` defines weekly editorial issues covering a Friday-to-Thursday window.
- `backend/app/models/social_post.py` defines Instagram publishing drafts linked to events or weekly issues, including planned/exported/manual-post timestamps.
- `backend/app/schemas/city.py` defines API output shape for cities.
- `backend/app/schemas/venue.py` defines API input and output shape for venues.
- `backend/app/schemas/event.py` defines API input and output shape for events.
- `backend/app/schemas/social_post.py` defines API output and edit shapes for generated social drafts.
- `backend/app/services/seed.py` idempotently creates the Glasgow city, manual source, and seeded venues.
- `backend/app/services/city_brands.py` creates city brands from templates and syncs brand metadata and starter venues.
- `backend/app/services/normalization.py` builds event slugs, dedupe fingerprints, confidence scores, and review flags.
- `backend/app/services/ingestion.py` runs enabled source adapters, logs source runs, deduplicates source IDs/fingerprints during ingest, and upserts normalised events into the shared `Event` model.
- `backend/app/services/deduplication.py` merges duplicates using event title, venue, event date, and city.
- `backend/app/services/weekly.py` creates Friday-to-Thursday weekly issues and draft Instagram roundup posts.
- `backend/app/services/weekly_run.py` orchestrates the automated weekly workflow: ingest, venue coverage, dedupe, scoring, candidate selection, review posts, and exports.
- `backend/app/services/social_generation.py` generates Instagram drafts, captions, hashtags, alt text, PNG exports, scheduling JSON, and review-queue payloads.
- `backend/app/services/meta_publishing.py` checks Meta Graph API readiness and prepares placeholder payloads without publishing.
- `backend/app/services/venue_coverage.py` seeds the expanded Glasgow venue database, audits coverage, checks individual venues, scores completeness, and builds weekly preflight reports.
- `backend/app/sources/base.py` defines the source adapter protocol and normalised source event shape.
- `backend/app/sources/ticketmaster.py` fetches Glasgow music events through Ticketmaster Discovery API using `apikey`, `city=Glasgow`, `countryCode=GB`, `classificationName=music`, and a 30-day date range.
- `backend/app/sources/manual_csv.py` imports legally provided manual event data from CSV.
- `backend/app/sources/bandsintown.py` is a placeholder for a future official Bandsintown integration.
- `backend/app/sources/songkick.py` is a placeholder for a future official Songkick integration.
- `backend/app/sources/venue_page.py` is a placeholder with robots.txt and terms-aware implementation notes.
- `backend/app/sources/registry.py` registers the default source adapter list.
- `backend/seeds/glasgow_venues.json` contains the initial Glasgow venue whitelist.
- `backend/seeds/glasgow_venue_coverage.json` contains the expanded Glasgow venue coverage seed list.
- `backend/seeds/manual_events.csv` provides sample manual event input for local ingestion testing.
- `backend/tests/test_ingestion_helpers.py` covers fingerprint creation, Ticketmaster query parameters, venue coverage seed integrity, pre-publish safety, and the Friday-to-Thursday weekly window.

### Frontend

- `frontend/package.json` declares the Next.js, React, TypeScript, and Tailwind app dependencies and scripts.
- `frontend/package-lock.json` pins the exact installed frontend dependency graph.
- `frontend/next.config.mjs` configures Next.js.
- `frontend/postcss.config.mjs` wires Tailwind and Autoprefixer into PostCSS.
- `frontend/tailwind.config.ts` defines the Gigged Glasgow colour palette, typography, and Tailwind scan paths.
- `frontend/tsconfig.json` configures strict TypeScript and the `@/*` import alias.
- `frontend/next-env.d.ts` provides Next.js TypeScript references.
- `frontend/app/globals.css` sets Tailwind layers and the global dark poster-style page background.
- `frontend/app/layout.tsx` defines metadata and loads the shared shell.
- `frontend/app/page.tsx` renders the main radar dashboard with stats, events, and social preview.
- `frontend/app/admin/page.tsx` renders the admin dashboard route.
- `frontend/app/admin/actions.ts` contains server actions that proxy social review operations with the backend admin token.
- `frontend/app/admin/events-inbox/page.tsx` renders the intake desk with manual event and CSV upload controls.
- `frontend/app/admin/needs-review/page.tsx` renders the moderation queue for uncertain events.
- `frontend/app/admin/approved-events/page.tsx` renders publish-ready events.
- `frontend/app/admin/venue-coverage/page.tsx` renders the Glasgow venue coverage dashboard, coverage score, source gaps, and Check now controls.
- `frontend/app/admin/weekly/page.tsx` renders the weekly issue builder and carousel preview.
- `frontend/app/admin/social/page.tsx` renders the social post generator and review queue.
- `frontend/app/admin/instagram/page.tsx` renders Instagram account readiness and manual export status.
- `frontend/app/admin/brand-settings/page.tsx` renders brand controls and guidelines.
- `frontend/app/admin/city-settings/page.tsx` renders live city brands and lets the operator create brands from templates.
- `frontend/app/admin/source-settings/page.tsx` renders source adapter settings and compliance notes.
- `frontend/app/brand/page.tsx` renders the complete Gigged Glasgow brand system.
- `frontend/app/events/page.tsx` renders the event list route.
- `frontend/app/venues/page.tsx` renders the venue whitelist route.
- `frontend/components/layout/Shell.tsx` defines global navigation and page framing.
- `frontend/components/brand/LogoMark.tsx` contains the SVG glyph and lockup logo concepts.
- `frontend/components/brand/BrandSystem.tsx` presents the palette, typography rules, logo, and template system.
- `frontend/components/admin/AdminDashboard.tsx` lays out the admin overview, venue whitelist, and post preview.
- `frontend/components/admin/StatCard.tsx` renders reusable dashboard metrics.
- `frontend/components/admin/PostPreview.tsx` re-exports the current social post preview component for admin compatibility.
- `frontend/components/admin/SocialReviewQueue.tsx` renders generated social drafts with approve, edit, reject, and regenerate controls.
- `frontend/components/admin/AdminSectionNav.tsx` provides admin workspace navigation and page headers.
- `frontend/components/admin/EventBoard.tsx` provides event moderation cards and duplicate merge controls.
- `frontend/components/admin/ManualEventPanel.tsx` provides manual event entry and CSV upload forms.
- `frontend/components/social/SocialPostPreview.tsx` renders Instagram-ready post and carousel template previews.
- `frontend/components/social/SocialTemplateGrid.tsx` displays all brand social templates together.
- `frontend/components/events/EventList.tsx` renders upcoming event rows with review status.
- `frontend/components/venues/VenueGrid.tsx` renders seeded venue cards.
- `frontend/lib/api.ts` contains typed server-side API fetch helpers with safe empty-state fallbacks.
- `frontend/lib/brand.ts` documents the core brand tokens in code.
- `frontend/lib/types.ts` defines TypeScript types matching backend API responses.

## Adding Another City

Gigged Glasgow is now structured as a multi-city engine with Glasgow as the
first live brand. A city template includes:

- `city_name`
- `brand_name`
- `handle`
- `tagline`
- `colours`
- `venues`
- `coordinates`
- `radius_km`
- `hashtags`
- `voice_notes`
- `default_posting_schedule`

Templates live in `backend/app/cities/`. Glasgow is defined in
`backend/app/cities/glasgow.py`; example templates for Gigged Edinburgh, Gigged
Manchester, and Gigged Liverpool live in `backend/app/cities/examples.py`.
`backend/app/cities/registry.py` exposes the template registry.

From the dashboard, go to `/admin/city-settings` and create a new brand from a
template. The backend creates a `City`, a linked `CityBrand`, and starter venue
rows. Existing Glasgow workflows remain the default because API calls still
default to `city=glasgow`.

Relevant endpoints:

- `GET /api/v1/admin/city-templates`
- `GET /api/v1/admin/city-brands`
- `POST /api/v1/admin/city-brands/{template_slug}`

For a brand beyond the provided examples, add a new `CityConfig` and register it
in `backend/app/cities/registry.py`.
