# Button And Action Audit

Status: complete for the current visible MVP workflow. Dynamic row actions are listed once per action type.

| Action | File | What it did before | Change made | Complete |
| --- | --- | --- | --- | --- |
| Main nav links: Radar, Admin, Brand, Events, Venues | `frontend/components/layout/Shell.tsx` | Navigated to real pages. | Added Settings link to the main navigation. | Yes |
| Logo home link | `frontend/components/brand/LogoMark.tsx` | Navigated home. | No change needed. | Yes |
| Admin section tabs | `frontend/components/admin/AdminSectionNav.tsx` | Navigated to admin sub-pages. | Added Settings tab. Existing links point to real pages. | Yes |
| Dashboard shortcut link to venues | `frontend/components/admin/AdminDashboard.tsx` | Navigated to public venues page. | No change needed. | Yes |
| City template create button | `frontend/app/admin/city-settings/page.tsx` | Called a backend admin endpoint. | Added loading state with `SubmitButton`; disabled state remains when already created. | Yes |
| Source enable/save action | `frontend/app/admin/source-settings/page.tsx` | Static source cards with no action. | Replaced with real source records from `GET /api/sources` and `PATCH /api/sources/{id}` forms. | Yes |
| Settings save button | `frontend/components/admin/SettingsForm.tsx` | Did not exist. | Added full Settings page with server-side save action, validation, loading, success and error messages. | Yes |
| Settings Ticketmaster test | `frontend/components/admin/SettingsForm.tsx` | Did not exist. | Added real `POST /api/settings/test-ticketmaster` action. | Yes |
| Settings Instagram test | `frontend/components/admin/SettingsForm.tsx` | Did not exist. | Added real `POST /api/settings/test-instagram` readiness check. | Yes |
| Settings test all | `frontend/components/admin/SettingsForm.tsx` | Did not exist. | Added real `POST /api/settings/test-all` action. | Yes |
| Weekly run/generate roundup | `frontend/app/admin/weekly/page.tsx` | Called older weekly-generation endpoint. | Wired to `POST /api/weekly/run`, which ingests, checks coverage, dedupes, scores, creates issue and drafts posts. Added loading state. | Yes |
| Event approve/reject/top-pick/sponsored | `frontend/components/admin/EventBoard.tsx` | Approve/reject/top-pick worked through admin routes; sponsored used admin route. | Approve/reject/top-pick now use requested event endpoints; all have loading states. Sponsored remains a real admin route. | Yes |
| Event merge duplicate | `frontend/components/admin/EventBoard.tsx` | Submitted to backend merge route. | Added loading state. | Yes |
| Event edit/save | `frontend/components/admin/EventBoard.tsx` | Submitted to backend edit route. | Wired to requested `PATCH /api/events/{id}` and added loading state. | Yes |
| Manual event add | `frontend/components/admin/ManualEventPanel.tsx` | Added event through admin manual route. | Wired to requested `POST /api/events`; added title validation and loading state. | Yes |
| CSV import | `frontend/components/admin/ManualEventPanel.tsx` | Imported CSV through backend route. | Kept real CSV import and added loading state. | Yes |
| Social generate drafts | `frontend/components/admin/SocialReviewQueue.tsx` | Called backend draft generation. | Added loading state. | Yes |
| Social save edits | `frontend/components/admin/SocialReviewQueue.tsx` | Submitted edits to backend. | Wired to requested `PATCH /api/social/posts/{id}` and added loading state. | Yes |
| Social approve/reject/regenerate | `frontend/components/admin/SocialReviewQueue.tsx` | Called admin social routes. | Wired to requested social post endpoints and added loading states. | Yes |
| Social schedule | `frontend/components/admin/SocialReviewQueue.tsx` | Real only for approved posts; otherwise static disabled text. | Kept disabled only when invalid, with explanatory title; approved posts submit to real schedule endpoint. | Yes |
| Social export | `frontend/components/admin/SocialReviewQueue.tsx` | Export path was displayed but no visible export action in queue. | Added real `POST /api/social/posts/{id}/export` button. | Yes |
| Social mark posted | `frontend/components/admin/SocialReviewQueue.tsx` | Backend existed but no visible queue button. | Added real `POST /api/social/posts/{id}/mark-posted` button. | Yes |
| Social copy caption/hashtags/alt text | `frontend/components/admin/SocialReviewQueue.tsx` | Copy endpoints existed but no visible copy buttons. | Added clipboard buttons with copied success state and disabled empty state. | Yes |
| Venue seed | `frontend/app/admin/venue-coverage/page.tsx` | Seeded Glasgow coverage through admin route. | Kept real action and added loading state. | Yes |
| Venue check all | `frontend/app/admin/venue-coverage/page.tsx` | Checked all venues through admin route. | Wired to requested `POST /api/venues/bulk-check`; added loading state. | Yes |
| Venue check now | `frontend/app/admin/venue-coverage/page.tsx` | Checked one venue through admin route. | Wired to requested `POST /api/venues/{id}/check`; added loading state. | Yes |
| Venue mark manual-only | `frontend/app/admin/venue-coverage/page.tsx` | Did not exist. | Added real `POST /api/venues/{id}/mark-manual-only` action. | Yes |
| Venue mark source broken | `frontend/app/admin/venue-coverage/page.tsx` | Did not exist. | Added real `POST /api/venues/{id}/mark-source-broken` action. | Yes |
| Venue add | `frontend/app/admin/venue-coverage/page.tsx` | Did not exist on coverage page. | Added real `POST /api/venues` form. | Yes |
| Venue edit | `frontend/app/admin/venue-coverage/page.tsx` | Did not exist on coverage page. | Added per-venue `PATCH /api/venues/{id}` form. | Yes |
| Venue merge duplicate | `frontend/app/admin/venue-coverage/page.tsx` | Did not exist on coverage page. | Added real `POST /api/venues/{keeper}/merge/{duplicate}` form. | Yes |
| Open venue website | `frontend/app/admin/venue-coverage/page.tsx` | Website URLs were text-only metadata. | Added working external links when URL exists. | Yes |
| Open event source URL | `frontend/app/admin/venue-coverage/page.tsx` | Event/source URLs were text-only metadata. | Added working external source URL links when URL exists. | Yes |

Notes:

- Placeholder provider integrations remain intentionally disabled at the source level until official API work is implemented.
- Manual-only and disabled states are explicit states, not dead buttons.
- `npm run test:buttons` checks for placeholder links, console-only interaction, and unowned raw buttons in the frontend.
