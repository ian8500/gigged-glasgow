# Frontend Rescue Report

## Goal

Make Gigged Glasgow usable as a manual-first gig curation tool:

Venue check -> Add gig -> Approve gig -> Build weekly copy -> Copy/export for Instagram.

No new APIs, scraping, Eventbrite/Ticketmaster dependency, or Instagram automation were added.

## What Was Broken Or Confusing

- Primary navigation pointed at mixed legacy/admin surfaces instead of the core workflow.
- Required workflow routes were missing:
  - `/events/new`
  - `/weekly`
  - `/social`
- The dashboard looked like a marketing/radar page instead of an operational manual curation dashboard.
- Settings exposed connection-test and enable buttons for automation sources, including Eventbrite, Bandsintown, Songkick, and Instagram, which made optional/future automation look like required functionality.
- Frontend API helpers returned null fallbacks for some reads, but did not expose safe mutation helpers for the core workflow.
- Several UI actions lived only inside admin pages and were not available from the simple workflow.
- The UI could become empty or unclear when the backend was down.
- `npm run lint` was not usable in non-interactive mode because ESLint was not configured or installed.
- `npm run test:ui` checked older routes instead of the required rescue routes.

## What Was Removed From The Main Workflow

- Removed `/admin` and `/brand` from the visible navigation.
- Removed automation/source settings from the main Settings page.
- Removed connection-test buttons for Ticketmaster, Eventbrite, Bandsintown, Songkick, and Instagram from the main Settings page.
- Removed any implication in the main workflow that Eventbrite, Ticketmaster, Songkick, Bandsintown, or Instagram automation is required.

Legacy admin routes still exist in the codebase for now, but they are no longer part of the main navigation or manual-first workflow.

## What Was Fixed

### Navigation

Navigation now contains only working core pages:

- Dashboard: `/`
- Venues: `/venues`
- Add Gig: `/events/new`
- Events: `/events`
- Weekly: `/weekly`
- Social Posts: `/social`
- Settings: `/settings`

### API Client

`frontend/lib/api.ts` was rebuilt around safe reads and safe mutations.

It now:

- Uses `NEXT_PUBLIC_API_BASE_URL`.
- Uses `ADMIN_API_KEY` for server-side admin requests.
- Catches failed requests.
- Returns safe fallback data for page rendering.
- Avoids uncaught backend failures during server rendering.
- Exposes the requested helpers:
  - `getDashboard()`
  - `getVenues()`
  - `getEvents()`
  - `getVenueCoverage()`
  - `getSettings()`
  - `saveSettings()`
  - `createEvent()`
  - `updateEvent()`
  - `approveEvent()`
  - `rejectEvent()`
  - `generateWeeklyIssue()`
  - `getSocialPosts()`
  - `exportSocialPost()`

### Dashboard

The dashboard now shows:

- Venues
- Upcoming gigs
- Needs review
- Generated posts
- Working quick links for venue watchlist, add gig, review events, and weekly builder
- Backend unavailable/empty fallback messaging

### Venue Watchlist

The venues page now supports the manual venue-check workflow:

- Venue name
- Address/postcode
- Website
- Events page
- Ticket page
- Instagram handle
- Last checked
- Coverage status
- Notes

Working buttons:

- Open events page
- Open website
- Open Instagram
- Add gig for this venue
- Mark checked

Frontend fallback buttons:

- Mark no gigs found

TODO: `Mark no gigs found` is currently browser-local only. Add a backend endpoint if this should persist.

### Add Gig

Created `/events/new`.

Fields:

- Event title
- Artist
- Venue dropdown
- Date
- Time
- Price
- Ticket URL
- Image URL
- Genre
- Notes
- Top pick
- Hidden gem
- Cheap gig

Working buttons:

- Save gig
- Save and add another
- Cancel

Backend limitation:

- The current event create endpoint persists title, venue, date/time, ticket URL, genre, price, notes, and top-pick where supported.
- Artist, image URL, hidden gem, and cheap gig are shown in the form but need backend schema support before they can persist fully.

### Events Review

The events page now has filters:

- All
- This week
- Weekend
- Needs review
- Approved
- Top picks
- Hidden gems
- Cheap gigs

Working buttons:

- Approve
- Reject
- Edit
- Mark top pick

Hidden/future:

- Mark hidden gem is not shown because the backend does not currently support it.

### Weekly Issue Builder

Created `/weekly`.

It shows approved gigs and builds frontend-only copy previews for:

- Weekly issue
- Weekend picks
- Cheap gigs
- Hidden gem

This intentionally avoids the backend weekly automation route because the current backend weekly run can trigger ingestion/coverage automation. The manual preview remains useful with zero API keys.

### Social Posts

Created `/social`.

It shows generated posts when available and a fallback example when none exist.

Each post includes:

- Title
- Caption
- Hashtags
- Alt text
- Status

Working buttons:

- Copy caption
- Copy hashtags
- Copy alt text
- Mark as posted manually
- Export files, only for real backend posts

No Instagram automation was added.

### Settings

Settings is now simple and manual-first:

- Brand
- Manual posting
- Optional future APIs

API copy now states:

> Optional future automation — not required.

Eventbrite is labelled:

> Saved credential only — adapter not implemented yet

Saving settings fails gracefully if the backend is unavailable.

### Testing

Added a working non-interactive lint setup:

- `.eslintrc.json`
- `eslint`
- `eslint-config-next@14.2.3`

Updated `npm run test:ui` to confirm these routes exist and build:

- `/`
- `/venues`
- `/events`
- `/events/new`
- `/weekly`
- `/social`
- `/settings`

## What Is Still Future / Optional

- Persisting `Mark no gigs found`.
- Persisting artist as a separate field from manual event creation.
- Persisting image URL from manual event creation.
- Persisting hidden gem and cheap gig flags as first-class backend fields.
- A backend weekly generation endpoint that only uses already-approved manual gigs and does not trigger ingestion/scraping.
- Instagram automation. Current workflow is manual copy/export only.
- Eventbrite, Ticketmaster, Songkick, and Bandsintown automation. These are optional future APIs and not required for the frontend to be useful.

## Verification

Passed:

- `npm run typecheck`
- `npm run lint`
- `npm run build`
- `npm run test:ui`
- Dev server HTTP checks returned `200` for `/`, `/venues`, `/events`, `/events/new`, `/weekly`, `/social`, and `/settings`.

Note: The in-app browser was not available in this session, so visual browser screenshots could not be captured.
