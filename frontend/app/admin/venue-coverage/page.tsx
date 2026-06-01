import {
  checkAllVenues,
  checkVenueNow,
  createVenue,
  editVenue,
  markVenueChecked,
  markVenueManualOnly,
  markVenueSourceBroken,
  mergeDuplicateVenues,
  seedVenueCoverage
} from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SubmitButton } from "@/components/admin/SubmitButton";
import { getVenueCoverage } from "@/lib/api";

const statusTone: Record<string, string> = {
  active: "border-clyde/30 bg-clyde/10 text-clyde",
  needs_review: "border-acid/30 bg-acid/10 text-acid",
  closed: "border-bone/20 bg-bone/10 text-bone/55",
  duplicate: "border-poster/40 bg-poster/10 text-poster",
  inactive: "border-bone/20 bg-bone/10 text-bone/55"
};

const coverageTone: Record<string, string> = {
  automated: "border-clyde/30 bg-clyde/10 text-clyde",
  manual_only: "border-acid/30 bg-acid/10 text-acid",
  broken: "border-poster/40 bg-poster/10 text-poster",
  unsupported: "border-bone/20 bg-bone/10 text-bone/60"
};

export default async function VenueCoveragePage() {
  const coverage = await getVenueCoverage();
  const summary = coverage.summary;

  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Audit" title="Glasgow Venue Coverage">
        <div className="flex flex-wrap gap-3">
          <form action={seedVenueCoverage}>
            <SubmitButton pendingText="Seeding" className="rounded-md border border-bone/15 px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-bone hover:bg-bone/10">
              Seed venues
            </SubmitButton>
          </form>
          <form action={checkAllVenues}>
            <SubmitButton pendingText="Checking" className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
              Check all
            </SubmitButton>
          </form>
        </div>
      </AdminPageHeader>

      <section className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <div className="rounded-lg border border-acid/25 bg-acid/10 p-6">
          <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">Broad coverage estimate</p>
          <div className="mt-4 font-display text-7xl font-black leading-none text-bone">
            {summary.coverage_score}%
          </div>
          <p className="mt-4 text-sm font-semibold text-bone/70">{summary.explanation}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Total venues discovered" value={summary.total_venues_discovered} />
          <Metric label="Currently monitored" value={summary.venues_currently_monitored} />
          <Metric label="Successful event pulls" value={summary.venues_with_successful_event_pulls} />
          <Metric label="No events found" value={summary.venues_with_no_events_found} />
          <Metric label="Manual review" value={summary.venues_needing_manual_review} />
          <Metric label="Broken source links" value={summary.broken_source_links} />
          <Metric label="Possible duplicates" value={summary.possible_duplicates} />
          <Metric label="Not checked in 30 days" value={summary.venues_not_checked_30_days} />
          <Metric label="API-covered venues" value={summary.api_covered_venues ?? 0} />
          <Metric label="Feed-covered venues" value={summary.feed_covered_venues ?? 0} />
          <Metric label="Structured-data venues" value={summary.structured_data_venues ?? 0} />
          <Metric label="Selector-supported venues" value={summary.selector_supported_venues ?? 0} />
          <Metric label="Blocked/unsupported venues" value={summary.blocked_unsupported_venues ?? summary.unsupported} />
          <Metric label="Partner required" value={summary.partner_required_venues ?? 0} />
          <Metric label="Sources needing credentials" value={summary.sources_needing_credentials ?? 0} />
          <Metric label="Sources needing permission" value={summary.sources_needing_permission ?? 0} />
          <Metric label="Sources failing" value={summary.sources_failing ?? 0} />
          <Metric label="Sources working" value={summary.sources_working ?? 0} />
        </div>
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="font-display text-2xl font-black text-bone">What is missing</h2>
            <p className="mt-2 max-w-3xl text-sm text-bone/58">
              Weekly roundup generation runs these venue checks first, flags suspicious gaps, and then builds the gig list.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="border-clyde/30 bg-clyde/10 text-clyde">{summary.automated} automated</Badge>
            <Badge tone="border-acid/30 bg-acid/10 text-acid">{summary.manual_only} manual-only</Badge>
            <Badge tone="border-bone/20 bg-bone/10 text-bone/60">{summary.unsupported} unsupported</Badge>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {summary.missing.map((item) => (
            <div key={item} className="rounded-md border border-bone/10 bg-ink/45 p-4 text-sm font-semibold text-bone/72">
              {item}
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <form action={createVenue} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Add venue</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <input name="name" required placeholder="Venue name" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <input name="postcode" placeholder="Postcode" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <input name="address" placeholder="Address" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone md:col-span-2" />
            <input name="website_url" placeholder="Official website" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <input name="event_listings_url" placeholder="Events page URL" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <input name="official_events_url" placeholder="Official events URL" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <input name="feed_url" placeholder="RSS / iCal feed URL" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <select name="source_mode" defaultValue="manual_only" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
              <option value="manual_only">Manual-only</option>
              <option value="feed">Feed</option>
              <option value="structured_data">Structured data</option>
              <option value="unsupported">Unsupported</option>
              <option value="api">API</option>
            </select>
            <input name="ticketing_url" placeholder="Ticketing URL" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <input name="instagram_handle" placeholder="@instagram" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
            <select name="coverage_status" defaultValue="manual_only" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
              <option value="manual_only">Manual-only</option>
              <option value="automated">Automated</option>
              <option value="needs_review">Needs review</option>
            </select>
            <textarea name="notes" placeholder="Notes" className="min-h-20 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone md:col-span-2" />
            <textarea name="selector_config" placeholder='{"event_container":".event","title":".title","starts_at":".date"}' className="min-h-20 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone md:col-span-2" />
          </div>
          <SubmitButton pendingText="Adding" className="mt-4 rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
            Add venue
          </SubmitButton>
        </form>

        <form action={mergeDuplicateVenues} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Merge duplicate venues</h2>
          <div className="mt-4 grid gap-3">
            <select name="keeperId" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
              {coverage.venues.map((venue) => (
                <option key={venue.id} value={venue.id}>
                  Keep {venue.venue_name}
                </option>
              ))}
            </select>
            <select name="duplicateId" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
              {coverage.venues.map((venue) => (
                <option key={venue.id} value={venue.id}>
                  Merge {venue.venue_name}
                </option>
              ))}
            </select>
          </div>
          <SubmitButton pendingText="Merging" className="mt-4 rounded-md border border-clyde px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-clyde">
            Merge duplicate venues
          </SubmitButton>
        </form>
      </section>

      <section className="rounded-lg border border-bone/10 bg-ink/45">
        <div className="border-b border-bone/10 p-5">
          <h2 className="font-display text-2xl font-black text-bone">Venue audit table</h2>
          <p className="mt-1 text-sm text-bone/55">
            Every possible venue is kept, including manual-only and venues with no current events.
          </p>
        </div>
        <div className="divide-y divide-bone/10">
          {coverage.venues.map((venue) => (
            <article key={venue.id} className="grid gap-4 p-5 xl:grid-cols-[1.1fr_1fr_260px]">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-display text-xl font-black text-bone">{venue.venue_name}</h3>
                  <Badge tone={statusTone[venue.status] ?? statusTone.needs_review}>{venue.status.replace("_", " ")}</Badge>
                  <Badge tone={coverageTone[venue.coverage_status] ?? coverageTone.manual_only}>
                    {venue.coverage_status.replace("_", " ")}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-bone/55">
                  {[venue.address, venue.postcode].filter(Boolean).join(", ") || "Address not stored"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold uppercase tracking-[0.12em] text-bone/45">
                  {venue.event_listings_url ? <span>events page</span> : <span>no events page</span>}
                  {venue.official_events_url ? <span>official source</span> : <span>no official source</span>}
                  {venue.feed_url ? <span>feed</span> : <span>no feed</span>}
                  <span>{venue.source_mode.replace("_", " ")}</span>
                  {venue.ticketing_url ? <span>ticket link</span> : <span>no ticket link</span>}
                  {venue.instagram_handle ? <span>{venue.instagram_handle}</span> : <span>no instagram</span>}
                </div>
              </div>

              <div className="text-sm text-bone/62">
                <p>
                  <span className="font-black text-bone/80">Last checked:</span>{" "}
                  {venue.last_checked_at ? venue.last_checked_at.slice(0, 10) : "Never"}
                </p>
                <p className="mt-1">
                  <span className="font-black text-bone/80">Last event found:</span>{" "}
                  {venue.last_event_found_at ? venue.last_event_found_at.slice(0, 10) : "None yet"}
                </p>
                <p className="mt-1">
                  <span className="font-black text-bone/80">Last success:</span>{" "}
                  {venue.last_success_at ? venue.last_success_at.slice(0, 10) : "None yet"}
                </p>
                <p className="mt-3 line-clamp-2">{venue.latest_check?.message ?? venue.notes ?? "No check log yet."}</p>
                {venue.latest_check?.diagnostic_summary ? (
                  <pre className="mt-3 max-h-32 overflow-auto rounded-md border border-bone/10 bg-night p-3 text-xs text-bone/55">
                    {JSON.stringify(venue.latest_check.diagnostic_summary, null, 2)}
                  </pre>
                ) : null}
                {venue.latest_check ? (
                  <p className="mt-2 font-black text-acid">
                    Confidence {Math.round(venue.latest_check.confidence_score * 100)}%
                  </p>
                ) : null}
              </div>

              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  {venue.website_url ? (
                    <a href={venue.website_url} target="_blank" rel="noreferrer" className="rounded-md border border-bone/15 px-3 py-2 text-center text-xs font-black uppercase text-bone/70">
                      Website
                    </a>
                  ) : null}
                  {venue.event_listings_url ? (
                    <a href={venue.event_listings_url} target="_blank" rel="noreferrer" className="rounded-md border border-clyde px-3 py-2 text-center text-xs font-black uppercase text-clyde">
                      Source URL
                    </a>
                  ) : null}
                </div>
                <form action={checkVenueNow}>
                  <input type="hidden" name="venueId" value={venue.id} />
                  <SubmitButton pendingText="Checking" className="w-full rounded-md bg-bone px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink hover:bg-acid">
                    Check now
                  </SubmitButton>
                </form>
                <form action={markVenueManualOnly}>
                  <input type="hidden" name="venueId" value={venue.id} />
                  <SubmitButton pendingText="Marking" className="w-full rounded-md border border-acid px-3 py-2 text-xs font-black uppercase text-acid">
                    Mark manual-only
                  </SubmitButton>
                </form>
                <form action={markVenueChecked}>
                  <input type="hidden" name="venueId" value={venue.id} />
                  <SubmitButton pendingText="Marking" className="w-full rounded-md border border-clyde px-3 py-2 text-xs font-black uppercase text-clyde">
                    Mark checked
                  </SubmitButton>
                </form>
                <form action={markVenueSourceBroken}>
                  <input type="hidden" name="venueId" value={venue.id} />
                  <SubmitButton pendingText="Marking" className="w-full rounded-md border border-poster px-3 py-2 text-xs font-black uppercase text-poster">
                    Mark source broken
                  </SubmitButton>
                </form>
              </div>
              <form action={editVenue} className="xl:col-span-3 grid gap-3 rounded-md border border-bone/10 bg-bone/[0.03] p-4 md:grid-cols-3">
                <input type="hidden" name="venueId" value={venue.id} />
                <input name="name" defaultValue={venue.venue_name} className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="postcode" defaultValue={venue.postcode ?? ""} placeholder="Postcode" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <select name="coverage_status" defaultValue={venue.coverage_status} className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
                  <option value="automated">Automated</option>
                  <option value="manual_only">Manual-only</option>
                  <option value="broken">Broken</option>
                  <option value="needs_review">Needs review</option>
                  <option value="unsupported">Unsupported</option>
                </select>
                <input name="address" defaultValue={venue.address ?? ""} placeholder="Address" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="website_url" defaultValue={venue.website_url ?? ""} placeholder="Website" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="event_listings_url" defaultValue={venue.event_listings_url ?? ""} placeholder="Events page" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="official_events_url" defaultValue={venue.official_events_url ?? ""} placeholder="Official events URL" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="feed_url" defaultValue={venue.feed_url ?? ""} placeholder="RSS / iCal feed" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <select name="source_mode" defaultValue={venue.source_mode} className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
                  <option value="manual_only">Manual-only</option>
                  <option value="feed">Feed</option>
                  <option value="structured_data">Structured data</option>
                  <option value="unsupported">Unsupported</option>
                  <option value="api">API</option>
                </select>
                <input name="ticketing_url" defaultValue={venue.ticketing_url ?? ""} placeholder="Ticketing" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="instagram_handle" defaultValue={venue.instagram_handle ?? ""} placeholder="@instagram" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <input name="notes" defaultValue={venue.notes ?? ""} placeholder="Notes" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
                <textarea name="selector_config" defaultValue={venue.selector_config ? JSON.stringify(venue.selector_config) : ""} placeholder="Selector config JSON" className="min-h-20 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone md:col-span-3" />
                <SubmitButton pendingText="Saving" className="rounded-md border border-clyde px-3 py-2 text-sm font-black uppercase text-clyde md:col-span-3">
                  Edit venue
                </SubmitButton>
              </form>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <h2 className="font-display text-2xl font-black text-bone">Discovery sources</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {coverage.discovery_sources.map((source) => (
            <div key={source.name} className="rounded-md border border-bone/10 bg-ink/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-display text-lg font-black text-bone">{source.name}</h3>
                <span className="rounded bg-bone/10 px-2 py-1 text-xs font-black uppercase tracking-[0.12em] text-clyde">
                  {source.mode.replaceAll("_", " ")}
                </span>
              </div>
              <p className="mt-2 text-sm text-bone/55">{source.notes}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-bone/45">{label}</p>
      <p className="mt-3 font-display text-4xl font-black text-bone">{value}</p>
    </div>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: string }) {
  return (
    <span className={`rounded border px-2 py-1 text-xs font-black uppercase tracking-[0.12em] ${tone}`}>
      {children}
    </span>
  );
}
