# Button Audit

Status values: `working`, `fixed`, `hidden`, `future`.

| Label | Page/component | Expected action | Backend endpoint | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Gigged Glasgow home/logo | `components/brand/LogoMark.tsx` | Open the home radar page | n/a | working | Normal link to `/`. |
| Radar | `components/layout/Shell.tsx` | Open home page | n/a | working | Route exists. |
| Admin | `components/layout/Shell.tsx` | Open admin overview | n/a | working | Route exists. |
| Brand | `components/layout/Shell.tsx` | Open brand system | n/a | working | Route exists. |
| Events | `components/layout/Shell.tsx` | Open public events list | `GET /api/v1/events?city=glasgow` | working | Route exists. |
| Venues | `components/layout/Shell.tsx` | Open public venue list | `GET /api/v1/venues?city=glasgow` | working | Route exists. |
| Settings | `components/layout/Shell.tsx` | Open settings form | `GET /api/v1/settings` | working | Route exists; admin token required server-side. |
| Save settings | `components/admin/SettingsForm.tsx` | Save settings and secrets | `PATCH /api/v1/settings` | fixed | Error messages now include backend setup/token details. Secret fields remain masked. |
| Test Ticketmaster | `components/admin/SettingsForm.tsx` | Test configured Ticketmaster key | `POST /api/v1/settings/test-ticketmaster` | working | API key is optional; missing key returns an explanatory failure. |
| Test Eventbrite | `components/admin/SettingsForm.tsx` | Test configured Eventbrite token | `POST /api/v1/settings/test-eventbrite` | working | Optional official API source; missing token returns an explanatory failure. |
| Enable Eventbrite | `components/admin/SettingsForm.tsx` | Enable Eventbrite after token test | `POST /api/v1/settings/enable-eventbrite` | working | Optional source; does not scrape Eventbrite. |
| Test Bandsintown | `components/admin/SettingsForm.tsx` | Test configured Bandsintown settings | `POST /api/v1/settings/test-bandsintown` | working | Optional source. |
| Test Songkick | `components/admin/SettingsForm.tsx` | Test configured Songkick settings | `POST /api/v1/settings/test-songkick` | working | Optional partner source. |
| Test Instagram | `components/admin/SettingsForm.tsx` | Check Meta settings readiness | `POST /api/v1/settings/test-instagram` | working | Readiness only; no publishing automation. |
| Test all | `components/admin/SettingsForm.tsx` | Run all settings tests | `POST /api/v1/settings/test-all` | working | Optional keys may report not configured. |
| Seed venues | `app/admin/venue-coverage/page.tsx` | Seed Glasgow venue coverage | `POST /api/v1/admin/venue-coverage/seed/glasgow` | working | Requires Glasgow city seed first. |
| Check all | `app/admin/venue-coverage/page.tsx` | Run batch venue coverage preflight | `POST /api/v1/admin/venue-coverage/check-all?city=glasgow` | fixed | Now defaults to local preflight, not live website checks. |
| Add venue | `app/admin/venue-coverage/page.tsx` | Create a venue | `POST /api/v1/venues` | working | Adds Glasgow venue with manual/source metadata. |
| Merge duplicate venues | `app/admin/venue-coverage/page.tsx` | Move duplicate venue events to keeper | `POST /api/v1/venues/{keeper_id}/merge/{duplicate_id}` | working | Use carefully; no delete. |
| Website | `app/admin/venue-coverage/page.tsx` | Open venue website in a new tab | n/a | working | Visible only when URL exists. |
| Source URL | `app/admin/venue-coverage/page.tsx` | Open venue event source URL | n/a | working | Visible only when URL exists. |
| Check now | `app/admin/venue-coverage/page.tsx` | Check one venue source | `POST /api/v1/venues/{venue_id}/check` | working | Single-venue, robots-aware page/feed check. |
| Mark manual-only | `app/admin/venue-coverage/page.tsx` | Mark venue as manual-only | `POST /api/v1/venues/{venue_id}/mark-manual-only` | working | For venues without safe automation. |
| Mark checked | `app/admin/venue-coverage/page.tsx` | Record a manual check timestamp | `POST /api/v1/venues/{venue_id}/mark-checked` | fixed | Added for local/manual workflow. |
| Mark source broken | `app/admin/venue-coverage/page.tsx` | Flag source as broken | `POST /api/v1/venues/{venue_id}/mark-source-broken` | working | Updates venue and coverage source status. |
| Edit venue | `app/admin/venue-coverage/page.tsx` | Save venue metadata | `PATCH /api/v1/venues/{venue_id}` | working | Handles URLs, source mode, notes, selector JSON. |
| Add event | `components/admin/ManualEventPanel.tsx` | Add manual gig | `POST /api/v1/events` | working | Requires title, venue, datetime. |
| Import CSV | `components/admin/ManualEventPanel.tsx` | Import manual events from CSV | `POST /api/v1/admin/events/import-csv` | working | Optional admin workflow. |
| Approve | `components/admin/EventBoard.tsx` | Approve event | `POST /api/v1/events/{event_id}/approve` | working | Moves event to scheduled/approved state. |
| Reject | `components/admin/EventBoard.tsx` | Reject event | `POST /api/v1/events/{event_id}/reject` | working | Marks event rejected. |
| Top pick | `components/admin/EventBoard.tsx` | Mark event as top pick | `POST /api/v1/events/{event_id}/mark-top-pick` | working | Local editorial flag. |
| Sponsored | `components/admin/EventBoard.tsx` | Mark event sponsored | `POST /api/v1/admin/events/{event_id}/sponsored` | working | Local editorial flag. |
| Merge | `components/admin/EventBoard.tsx` | Merge duplicate events | `POST /api/v1/admin/events/{keeper_id}/merge/{duplicate_id}` | working | Keeps selected event. |
| Save event | `components/admin/EventBoard.tsx` | Save event edits | `PATCH /api/v1/events/{event_id}` | working | Edits title, date, ticket URL, genre, note. |
| Generate weekly roundup | `app/admin/weekly/page.tsx` | Run weekly workflow | `POST /api/v1/weekly/run?city=glasgow` | working | Uses seeded/local-safe coverage preflight. |
| Generate drafts | `components/admin/SocialReviewQueue.tsx` | Generate social post drafts | `POST /api/v1/admin/social/generate?city=glasgow` | working | Creates review drafts only. |
| Save edits | `components/admin/SocialReviewQueue.tsx` | Save social post edits | `PATCH /api/v1/social/posts/{post_id}` | working | Caption/title/description edits. |
| Approve | `components/admin/SocialReviewQueue.tsx` | Approve social post | `POST /api/v1/social/posts/{post_id}/approve` | working | Does not publish. |
| Schedule | `components/admin/SocialReviewQueue.tsx` | Mark approved post for manual scheduling | `POST /api/v1/admin/social/{post_id}/schedule` | working | Visible as disabled text until approved. |
| Regen | `components/admin/SocialReviewQueue.tsx` | Regenerate social draft | `POST /api/v1/social/posts/{post_id}/regenerate` | working | Requires source event/issue context. |
| Reject | `components/admin/SocialReviewQueue.tsx` | Reject social draft | `POST /api/v1/social/posts/{post_id}/reject` | working | Local status change. |
| Export | `components/admin/SocialReviewQueue.tsx` | Export PNG/JSON assets | `POST /api/v1/social/posts/{post_id}/export` | working | Local export only. |
| Mark posted | `components/admin/SocialReviewQueue.tsx` | Mark post manually posted | `POST /api/v1/social/posts/{post_id}/mark-posted` | working | No Instagram automation. |
| Copy caption | `components/admin/SocialReviewQueue.tsx` | Copy caption to clipboard | Browser clipboard | working | Client-side copy. |
| Copy hashtags | `components/admin/SocialReviewQueue.tsx` | Copy hashtags to clipboard | Browser clipboard | working | Client-side copy. |
| Copy alt | `components/admin/SocialReviewQueue.tsx` | Copy alt text to clipboard | Browser clipboard | working | Client-side copy. |
| Save source | `app/admin/source-settings/page.tsx` | Save source enabled/notes state | `PATCH /api/v1/sources/{source_id}` | working | Optional sources may reject enable without credentials. |
| Test source | `app/admin/source-settings/page.tsx` | Test source adapter | `POST /api/v1/sources/{source_id}/test` | working | Missing keys return explanatory failure. |
| Run source | `app/admin/source-settings/page.tsx` | Run one source ingest | `POST /api/v1/sources/{source_id}/ingest?city=glasgow` | working | Official/API/feed sources only. |
| Add feed | `app/admin/feeds/page.tsx` | Add RSS/Atom/iCal feed | `POST /api/v1/feeds` | working | Optional source workflow. |
| Test feed | `app/admin/feeds/page.tsx` | Test feed URL | `POST /api/v1/feeds/{feed_id}/test` | working | Optional source workflow. |
| Run feed | `app/admin/feeds/page.tsx` | Ingest feed | `POST /api/v1/feeds/{feed_id}/run` | working | Optional source workflow. |
| Disable feed | `app/admin/feeds/page.tsx` | Disable feed | `PATCH /api/v1/feeds/{feed_id}` | working | Optional source workflow. |
| Delete feed | `app/admin/feeds/page.tsx` | Delete feed | `DELETE /api/v1/feeds/{feed_id}` | working | Optional source workflow. |
| Approve submission | `app/admin/submissions/page.tsx` | Approve promoter submission | `POST /api/v1/submissions/{submission_id}/approve` | working | Submission workflow. |
| Reject submission | `app/admin/submissions/page.tsx` | Reject promoter submission | `POST /api/v1/submissions/{submission_id}/reject` | working | Submission workflow. |
| Create city | `app/admin/city-settings/page.tsx` | Create a city brand from template | `POST /api/v1/admin/city-brands/{template_slug}` | future | Present for expansion beyond Glasgow; not part of current core workflow. |
| Submit event | `app/submit/page.tsx` | Submit public/promoter event | `POST /api/v1/submissions` | working | Enters review, never publishes directly. |
