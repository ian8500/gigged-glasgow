import { checkAllVenues, checkVenueNow, seedVenueCoverage } from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
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
            <button className="rounded-md border border-bone/15 px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-bone hover:bg-bone/10">
              Seed venues
            </button>
          </form>
          <form action={checkAllVenues}>
            <button className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
              Check all
            </button>
          </form>
        </div>
      </AdminPageHeader>

      <section className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <div className="rounded-lg border border-acid/25 bg-acid/10 p-6">
          <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">Coverage score</p>
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

      <section className="rounded-lg border border-bone/10 bg-ink/45">
        <div className="border-b border-bone/10 p-5">
          <h2 className="font-display text-2xl font-black text-bone">Venue audit table</h2>
          <p className="mt-1 text-sm text-bone/55">
            Every possible venue is kept, including manual-only and venues with no current events.
          </p>
        </div>
        <div className="divide-y divide-bone/10">
          {coverage.venues.map((venue) => (
            <article key={venue.id} className="grid gap-4 p-5 xl:grid-cols-[1.2fr_1fr_180px]">
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
                <p className="mt-3 line-clamp-2">{venue.latest_check?.message ?? venue.notes ?? "No check log yet."}</p>
                {venue.latest_check ? (
                  <p className="mt-2 font-black text-acid">
                    Confidence {Math.round(venue.latest_check.confidence_score * 100)}%
                  </p>
                ) : null}
              </div>

              <div className="flex items-start justify-start xl:justify-end">
                <form action={checkVenueNow}>
                  <input type="hidden" name="venueId" value={venue.id} />
                  <button className="rounded-md bg-bone px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink hover:bg-acid">
                    Check now
                  </button>
                </form>
              </div>
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
