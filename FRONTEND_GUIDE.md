# Frontend Guide

## What To Do First

1. Start the backend and frontend.
2. Run `npm run doctor` from the project root.
3. Open `http://localhost:3000/settings` and confirm settings load.
4. Open `http://localhost:3000/admin/venue-coverage`.
5. Click `Seed venues` if the dashboard says coverage data is missing.
6. Click `Check all` to run the local venue coverage preflight.

API keys are optional for local use. The app works as a manual editorial tool with seeded venues and manually added gigs.

## Pages

`/` is the radar overview. It shows headline counts and a quick view of what the app knows.

`/venues` is the public venue list for Glasgow.

`/events` is the public event list for Glasgow.

`/admin` is the admin overview. Use it to see counts and jump into the operational pages.

`/admin/events-inbox` is the manual gig desk. Add gigs manually, upload CSVs, edit events, approve events, reject events, and merge duplicates.

`/admin/needs-review` shows events that need editorial approval.

`/admin/approved-events` shows events ready for weekly selection.

`/admin/venue-coverage` is the venue audit page. It shows which Glasgow venues are tracked, which ones are manual-only, which sources need review, and when venues were last checked.

`/admin/weekly` runs the weekly issue workflow.

`/admin/social` generates and reviews Instagram post drafts.

`/admin/instagram` shows manual export and future Meta API readiness.

`/settings` and `/admin/settings` save local API keys and app settings.

`/brand` shows the public brand system.

## Venue Coverage

Venue coverage means: “Do we know how this venue’s gigs should be tracked?”

`manual-only` means there is no safe automated source configured for that venue. You can still add gigs manually for it.

Use `Check all` for the normal local preflight. It does not run broad website scraping. It checks seeded venue/source metadata and records local status.

Use `Check now` on one venue when you want a venue-specific source check.

Use `Mark checked` when you manually reviewed a venue and want to record that timestamp.

Use `Mark manual-only` when a venue should stay manual.

Use `Mark source broken` when a stored event/source URL is no longer usable.

## Adding Gigs Manually

Go to `/admin/events-inbox`.

Use `Add manual event` with:

- event or artist title
- venue
- date and time
- ticket URL if available
- genre if useful

Manual gigs are scheduled immediately and can be used in the weekly workflow.

## Approving And Rejecting Gigs

Use `/admin/needs-review` for uncertain imported or submitted gigs.

Click `Approve` to make a gig eligible for publishing workflows.

Click `Reject` to keep it out of the public list and weekly issue.

Use `Save event` to fix title, date, ticket URL, genre, or editorial note.

## Weekly Issue

Go to `/admin/weekly`.

Click `Generate weekly roundup`.

This runs local-safe venue coverage preflight, dedupe, event scoring, weekly issue creation, and social draft generation. It does not publish anything automatically.

## Instagram Posts

Go to `/admin/social`.

Click `Generate drafts` after you have approved events.

For each draft:

- edit title, description, or caption
- click `Save edits`
- click `Approve` if it is ready
- click `Export` to create local PNG/JSON assets
- click `Copy caption`, `Copy hashtags`, or `Copy alt`
- click `Mark posted` after you post it manually

Instagram automation is not enabled. The current workflow is export and manual posting.

## Settings

Settings save to the backend database. Secret fields are stored server-side and shown back as masked values.

The backend and frontend must use the same `ADMIN_API_KEY`. If they do not match, admin actions return `401`.

`NEXT_PUBLIC_API_BASE_URL` should be:

```dotenv
http://localhost:8000/api/v1
```

## API Sources

API sources are optional for local operation.

Ticketmaster, Eventbrite, Bandsintown, and Songkick can be tested from Settings or Source Settings when credentials exist. Missing keys should show a clear message, not break the app.

Do not add scraping or Instagram automation. Current automation should use official APIs, safe feeds, seeded venue metadata, or manual entry.

## Every Week

1. Run `npm run doctor`.
2. Start backend and frontend.
3. Open `/admin/venue-coverage` and click `Check all`.
4. Add any missing gigs manually in `/admin/events-inbox`.
5. Approve or reject gigs in `/admin/needs-review`.
6. Open `/admin/weekly` and click `Generate weekly roundup`.
7. Open `/admin/social`, review drafts, approve, export, and copy captions.
8. Post manually on Instagram.
9. Click `Mark posted` for anything you published.
