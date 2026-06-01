"use client";

import { useMemo, useState, useTransition } from "react";
import { useFormState } from "react-dom";

import {
  markVenueCheckedAction,
  markVenueManualOnlyAction,
  scrapeVenueAction,
  updateVenueScraperConfigAction,
  type ActionState
} from "@/app/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { Venue } from "@/lib/types";

type LocalStatus = Record<number, { checked?: string; noGigs?: string; message?: string }>;

export function VenueGrid({ venues }: { venues: Venue[] }) {
  const [localStatus, setLocalStatus] = useState<LocalStatus>({});
  const [isPending, startTransition] = useTransition();
  const sortedVenues = useMemo(() => [...venues].sort((a, b) => a.name.localeCompare(b.name)), [venues]);

  function markChecked(venueId: number) {
    const formData = new FormData();
    formData.set("venueId", String(venueId));
    startTransition(async () => {
      const result = await markVenueCheckedAction(formData);
      setLocalStatus((current) => ({
        ...current,
        [venueId]: {
          ...current[venueId],
          checked: new Date().toISOString(),
          message: result.ok ? "Marked checked." : result.message
        }
      }));
    });
  }

  function markNoGigsFound(venueId: number) {
    setLocalStatus((current) => ({
      ...current,
      [venueId]: {
        ...current[venueId],
        noGigs: new Date().toISOString(),
        message: "No gigs found noted locally. Backend endpoint is future work."
      }
    }));
  }

  function autoCheck(venueId: number) {
    const formData = new FormData();
    formData.set("venueId", String(venueId));
    startTransition(async () => {
      const result = await scrapeVenueAction(formData);
      setLocalStatus((current) => ({
        ...current,
        [venueId]: {
          ...current[venueId],
          checked: new Date().toISOString(),
          message: result.ok
            ? `Auto check complete. Found ${result.data?.events_found ?? 0} possible gigs.`
            : result.message
        }
      }));
    });
  }

  function markManualOnly(venueId: number) {
    const formData = new FormData();
    formData.set("venueId", String(venueId));
    startTransition(async () => {
      const result = await markVenueManualOnlyAction(formData);
      setLocalStatus((current) => ({
        ...current,
        [venueId]: {
          ...current[venueId],
          message: result.ok ? "Venue marked manual-only." : result.message
        }
      }));
    });
  }

  return (
    <main className="space-y-6">
      <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Venue Watchlist</p>
          <h1 className="mt-2 font-display text-4xl font-black leading-none text-bone md:text-5xl">
            Manual venue checks
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/58">
            Open each venue source, add gigs manually, and record lightweight check status without relying on scraping.
          </p>
        </div>
        <a className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase text-ink" href="/events/new">
          Add Gig
        </a>
      </header>

      {sortedVenues.length ? (
        <section className="grid gap-4 lg:grid-cols-2">
          {sortedVenues.map((venue) => {
            const status = localStatus[venue.id];
            return (
              <VenueCard
                key={venue.id}
                autoCheck={autoCheck}
                isPending={isPending}
                markChecked={markChecked}
                markManualOnly={markManualOnly}
                markNoGigsFound={markNoGigsFound}
                status={status}
                venue={venue}
              />
            );
          })}
        </section>
      ) : (
        <EmptyState />
      )}
    </main>
  );
}

function VenueCard({
  venue,
  status,
  isPending,
  markChecked,
  markNoGigsFound,
  autoCheck,
  markManualOnly
}: {
  venue: Venue;
  status?: { checked?: string; noGigs?: string; message?: string };
  isPending: boolean;
  markChecked: (venueId: number) => void;
  markNoGigsFound: (venueId: number) => void;
  autoCheck: (venueId: number) => void;
  markManualOnly: (venueId: number) => void;
}) {
  const lastChecked = status?.checked ?? venue.last_checked_at;
  const [configState, formAction] = useFormState<ActionState, FormData>(updateVenueScraperConfigAction, {
    ok: false,
    message: ""
  });
  const config = venue.scraper_selector_config ?? venue.selector_config ?? null;

  return (
    <article className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
                <div className="flex flex-col justify-between gap-3 sm:flex-row">
                  <div>
                    <h2 className="font-display text-2xl font-black text-bone">{venue.name}</h2>
                    <p className="mt-2 text-sm leading-6 text-bone/58">
                      {[venue.address, venue.postcode].filter(Boolean).join(", ") || "Area/address not set"}
                    </p>
                  </div>
                  <span className="h-fit rounded bg-bone/10 px-3 py-1 text-xs font-black uppercase tracking-[0.12em] text-bone/62">
                    {venue.scraper_status || venue.coverage_status || venue.source_mode || "manual"}
                  </span>
                </div>

                <dl className="mt-5 grid gap-3 text-sm md:grid-cols-2">
                  <Meta label="Website" value={venue.website_url || venue.official_website_url} />
                  <Meta label="Events page" value={venue.event_listings_url || venue.official_events_url} />
                  <Meta label="Ticket page" value={venue.ticketing_url} />
                  <Meta label="Instagram" value={venue.instagram_handle} />
                  <Meta label="Last checked" value={formatDate(lastChecked)} />
                  <Meta label="Scraper mode" value={venue.source_mode} />
                  <Meta label="Scraper notes" value={venue.scraper_notes || venue.notes || status?.message || "No notes"} />
                </dl>

                {status?.message ? (
                  <p className="mt-4 rounded-md border border-clyde/25 bg-clyde/10 px-3 py-2 text-sm text-clyde">
                    {status.message}
                  </p>
                ) : null}

                <div className="mt-5 grid gap-2 sm:grid-cols-3">
                  <ExternalButton href={venue.event_listings_url || venue.official_events_url} label="Open events page" />
                  <ExternalButton href={venue.website_url || venue.official_website_url} label="Open website" />
                  <ExternalButton href={instagramUrl(venue.instagram_handle)} label="Open Instagram" />
                  <a
                    className="rounded-md border border-acid px-3 py-2 text-center text-xs font-black uppercase text-acid"
                    href={`/events/new?venue=${encodeURIComponent(venue.slug)}`}
                  >
                    Add gig
                  </a>
                  <button
                    className="rounded-md border border-amber px-3 py-2 text-xs font-black uppercase text-amber disabled:opacity-50"
                    disabled={isPending}
                    onClick={() => autoCheck(venue.id)}
                    type="button"
                  >
                    Auto check this venue
                  </button>
                  <button
                    className="rounded-md border border-bone/20 px-3 py-2 text-xs font-black uppercase text-bone/65 disabled:opacity-50"
                    disabled={isPending}
                    onClick={() => markManualOnly(venue.id)}
                    type="button"
                  >
                    Mark manual-only
                  </button>
                  <button
                    className="rounded-md border border-clyde px-3 py-2 text-xs font-black uppercase text-clyde disabled:opacity-50"
                    disabled={isPending}
                    onClick={() => markChecked(venue.id)}
                    type="button"
                  >
                    Mark checked
                  </button>
                  <button
                    className="rounded-md border border-bone/20 px-3 py-2 text-xs font-black uppercase text-bone/65"
                    onClick={() => markNoGigsFound(venue.id)}
                    type="button"
                  >
                    Mark no gigs found
                  </button>
                </div>

      <details className="mt-5 rounded-md border border-bone/10 bg-night/60 p-4">
        <summary className="cursor-pointer text-xs font-black uppercase tracking-[0.14em] text-clyde">
          Edit scraper config
        </summary>
        <form action={formAction} className="mt-4 grid gap-3">
          <input name="venueId" type="hidden" value={venue.id} />
          <label className="grid gap-2 text-sm font-bold text-bone/70">
            Source mode
            <select
              className="rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone"
              defaultValue={venue.source_mode || "manual_only"}
              name="source_mode"
            >
              <option value="manual_only">manual_only</option>
              <option value="structured_data">structured_data</option>
              <option value="rss">rss</option>
              <option value="ical">ical</option>
              <option value="selector">selector</option>
              <option value="unsupported">unsupported</option>
            </select>
          </label>
          <label className="grid gap-2 text-sm font-bold text-bone/70">
            Selector config JSON
            <textarea
              className="min-h-32 rounded-md border border-bone/10 bg-ink px-3 py-2 font-mono text-xs text-bone"
              defaultValue={config ? JSON.stringify(config, null, 2) : ""}
              name="scraper_selector_config"
              placeholder='{"event_card": ".event-card", "title": ".event-title", "date": ".event-date", "ticket_url": "a"}'
            />
          </label>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className={`text-sm ${configState.message ? (configState.ok ? "text-clyde" : "text-poster") : "text-bone/45"}`}>
              {configState.message || "Selectors are only used when source mode is selector."}
            </p>
            <SubmitButton pendingText="Saving" className="rounded-md border border-clyde px-3 py-2 text-xs font-black uppercase text-clyde">
              Save scraper config
            </SubmitButton>
          </div>
        </form>
      </details>
    </article>
  );
}

function Meta({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-black uppercase tracking-[0.16em] text-bone/35">{label}</dt>
      <dd className="mt-1 break-words text-bone/72">{value || "Not set"}</dd>
    </div>
  );
}

function ExternalButton({ href, label }: { href?: string | null; label: string }) {
  if (!href) {
    return (
      <button className="rounded-md border border-bone/10 px-3 py-2 text-xs font-black uppercase text-bone/30" disabled type="button">
        {label}
      </button>
    );
  }
  return (
    <a
      className="rounded-md border border-bone/15 px-3 py-2 text-center text-xs font-black uppercase text-bone/70"
      href={href}
      rel="noreferrer"
      target="_blank"
    >
      {label}
    </a>
  );
}

function EmptyState() {
  return (
    <section className="rounded-lg border border-dashed border-bone/20 bg-bone/[0.03] p-8 text-bone/58">
      <h2 className="font-display text-2xl font-black text-bone">No venues yet</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6">
        Backend unavailable or no Glasgow venues are seeded yet. Run backend then refresh, or seed the venue watchlist.
      </p>
    </section>
  );
}

function instagramUrl(handle?: string | null) {
  if (!handle) {
    return null;
  }
  const cleaned = handle.replace(/^@/, "").trim();
  return cleaned ? `https://www.instagram.com/${cleaned}/` : null;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Not checked yet";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
