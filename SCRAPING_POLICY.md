# Gigged Glasgow Scraping Policy

## What The Auto Finder Does

The Auto Finder checks only official venue event pages and feeds already stored against venue records in the Gigged Glasgow database.

Supported sources:

- Official venue event pages configured as `event_listings_url` or `official_events_url`
- Venue RSS or Atom feeds
- Venue iCal feeds
- JSON-LD `schema.org/Event` data embedded on venue pages
- Manually configured selector maps for simple venue pages

Every extracted gig is stored as an `ExtractedEventCandidate` with `status=needs_review`. Nothing is published automatically.

## What It Will Not Scrape

The Auto Finder must not scrape:

- Instagram
- Facebook
- TikTok
- Eventbrite web pages
- Skiddle web pages
- DICE
- Resident Advisor
- Pages behind login
- Paywalled pages
- CAPTCHA-protected pages
- Anti-bot-protected pages
- Pages blocked by `robots.txt`
- The wider internet

It does not use browser automation.

## Safety Rules

- Use the clear User-Agent `GiggedGlasgowBot/0.1`.
- Check `robots.txt` before fetching a configured venue URL.
- Use request timeouts.
- Limit response size.
- Store extracted fields and diagnostics only.
- Never store full copyrighted page HTML.
- Keep extracted events in review until a human approves or converts them.

## How To Run It

From the frontend:

1. Open `/scrape`.
2. Click `Run city scrape`.
3. Review extracted candidates.
4. Approve, reject, or convert candidates to events.

From curl:

```bash
curl -sS -X POST \
  -H "X-Admin-Token: change-me-in-production" \
  "http://localhost:8000/api/v1/admin/scrape/run?city=glasgow"
```

Check one venue:

```bash
curl -sS -X POST \
  -H "X-Admin-Token: change-me-in-production" \
  "http://localhost:8000/api/v1/admin/scrape/venues/1"
```

List candidates:

```bash
curl -sS \
  -H "X-Admin-Token: change-me-in-production" \
  "http://localhost:8000/api/v1/admin/scrape/candidates?city=glasgow"
```

## How To Add Event Page URLs

On `/venues`, edit the venue record so it has one of:

- `event_listings_url`
- `official_events_url`
- `feed_url`

Set `source_mode` to one of:

- `manual_only`
- `structured_data`
- `rss`
- `ical`
- `selector`
- `unsupported`

## Selector Config

Selectors are only used when a venue is explicitly set to `source_mode=selector`.

Example:

```json
{
  "event_card": ".event-card",
  "title": ".event-title",
  "date": ".event-date",
  "ticket_url": "a"
}
```

Use selector mode only for simple official venue pages where the venue permits automated checks.

## Review Workflow

The safe workflow is:

`Venue Watchlist -> Check all venues -> Extract possible gigs -> Review extracted gigs -> Approve/convert gigs -> Generate weekly posts`

Candidates do not appear as approved events until a human converts them.

## Manual Workflow Still Works

If Auto Finder finds nothing, the main workflow remains:

`Venues -> Add gig manually -> Approve -> Weekly -> Social posts`
