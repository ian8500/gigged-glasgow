"use client";

import { useMemo, useState } from "react";

import type { Event } from "@/lib/types";

const filters = ["all", "this week", "weekend", "top picks", "cheap gigs", "needs review"] as const;

type Filter = (typeof filters)[number];

export function EventList({ events }: { events: Event[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const visibleEvents = useMemo(() => events.filter((event) => matchesFilter(event, filter)), [events, filter]);

  return (
    <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Glasgow gig guide</p>
          <h2 className="mt-2 font-display text-3xl font-black leading-none text-bone md:text-4xl">
            Upcoming gigs
          </h2>
        </div>
        <span className="w-fit rounded bg-bone/10 px-3 py-1 text-sm text-bone/70">
          {visibleEvents.length} of {events.length} gigs
        </span>
      </div>

      <div className="mt-5 flex gap-2 overflow-x-auto pb-1">
        {filters.map((item) => (
          <button
            key={item}
            className={`shrink-0 rounded-md px-3 py-2 text-xs font-black uppercase ${
              filter === item ? "bg-acid text-ink" : "border border-bone/15 text-bone/62"
            }`}
            onClick={() => setFilter(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </div>

      <div className="mt-5 divide-y divide-bone/10">
        {visibleEvents.length === 0 ? (
          <div className="rounded-md border border-dashed border-bone/15 p-6 text-sm leading-6 text-bone/55">
            No gigs match this view yet. Add events through the gig desk, then approve them for publishing.
          </div>
        ) : (
          visibleEvents.map((event) => <EventRow key={event.id} event={event} />)
        )}
      </div>
    </section>
  );
}

function EventRow({ event }: { event: Event }) {
  return (
    <article className="grid gap-3 py-4 md:grid-cols-[1fr_190px]">
      <div className="min-w-0">
        <div className="flex flex-wrap gap-2">
          {event.top_pick ? <Badge tone="acid">Top pick</Badge> : null}
          {event.needs_review ? <Badge tone="poster">Needs review</Badge> : null}
          {cheapGig(event) ? <Badge tone="clyde">Cheap</Badge> : null}
        </div>
        <h3 className="mt-2 break-words font-display text-xl font-black leading-tight text-bone">
          {event.title}
        </h3>
        <p className="mt-1 text-sm leading-6 text-bone/60">
          {event.venue?.name ?? "Venue TBC"} · {event.genre ?? "Live music"}
        </p>
        {event.editorial_note ? (
          <p className="mt-2 max-w-3xl text-sm leading-6 text-bone/50">{event.editorial_note}</p>
        ) : null}
      </div>
      <div className="text-left md:text-right">
        <p className="font-semibold text-acid">{formatDate(event.starts_at)}</p>
        <p className="mt-1 text-sm text-bone/55">{formatPrice(event)}</p>
        {event.ticket_url ? (
          <a
            className="mt-3 inline-flex rounded-md border border-clyde px-3 py-2 text-xs font-black uppercase text-clyde"
            href={event.ticket_url}
            rel="noreferrer"
            target="_blank"
          >
            Tickets
          </a>
        ) : null}
      </div>
    </article>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: "acid" | "poster" | "clyde" }) {
  const tones = {
    acid: "bg-acid text-ink",
    poster: "bg-poster text-bone",
    clyde: "bg-clyde text-ink"
  };
  return <span className={`rounded px-2 py-1 text-xs font-black uppercase tracking-[0.12em] ${tones[tone]}`}>{children}</span>;
}

function matchesFilter(event: Event, filter: Filter) {
  const date = new Date(event.starts_at);
  if (filter === "all") return true;
  if (filter === "needs review") return event.needs_review;
  if (filter === "top picks") return Boolean(event.top_pick);
  if (filter === "cheap gigs") return cheapGig(event);
  if (filter === "weekend") return [5, 6, 0].includes(date.getDay());
  if (filter === "this week") return isThisWeek(date);
  return true;
}

function cheapGig(event: Event) {
  const price = Number(event.price_min ?? event.price_max ?? Number.NaN);
  return Number.isFinite(price) && price <= 15;
}

function isThisWeek(date: Date) {
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay() + 1);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 7);
  return date >= start && date < end;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date TBC";
  }
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function formatPrice(event: Event) {
  const currency = event.currency === "GBP" ? "£" : event.currency;
  if (event.price_min && event.price_max && event.price_min !== event.price_max) {
    return `${currency}${event.price_min}-${event.price_max}`;
  }
  if (event.price_min) {
    return `${currency}${event.price_min}`;
  }
  return "Price TBC";
}
