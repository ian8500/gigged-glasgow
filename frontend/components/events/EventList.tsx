"use client";

import { useMemo, useState } from "react";

import { approveEventAction, markTopPickAction, rejectEventAction, updateEventAction } from "@/app/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { AdminEvent } from "@/lib/types";

const filters = [
  "all",
  "this week",
  "weekend",
  "needs review",
  "approved",
  "top picks",
  "hidden gems",
  "cheap gigs"
] as const;

type Filter = (typeof filters)[number];

export function EventList({ events }: { events: AdminEvent[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const visibleEvents = useMemo(() => events.filter((event) => matchesFilter(event, filter)), [events, filter]);

  return (
    <main className="space-y-6">
      <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Events Review</p>
          <h1 className="mt-2 font-display text-4xl font-black leading-none text-bone md:text-5xl">Gig queue</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/58">
            Review manually added and imported gigs. Only working actions are shown.
          </p>
        </div>
        <a className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase text-ink" href="/events/new">
          Add Gig
        </a>
      </header>

      <div className="flex flex-wrap gap-2">
        {filters.map((item) => (
          <button
            key={item}
            className={`rounded-md px-3 py-2 text-xs font-black uppercase ${
              filter === item ? "bg-acid text-ink" : "border border-bone/15 text-bone/62"
            }`}
            onClick={() => setFilter(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </div>

      {visibleEvents.length ? (
        <section className="space-y-4">
          {visibleEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </section>
      ) : (
        <section className="rounded-lg border border-dashed border-bone/20 bg-bone/[0.03] p-8 text-bone/58">
          <h2 className="font-display text-2xl font-black text-bone">No gigs yet</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6">
            Nothing matches this filter. Add a gig manually, or run backend then refresh.
          </p>
        </section>
      )}
    </main>
  );
}

function EventCard({ event }: { event: AdminEvent }) {
  return (
    <article className="grid gap-5 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 xl:grid-cols-[1fr_340px]">
      <div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={event.needs_review ? "poster" : "clyde"}>{event.needs_review ? "Needs review" : event.status}</Badge>
          {event.top_pick ? <Badge tone="acid">Top pick</Badge> : null}
          {cheapGig(event) ? <Badge tone="neutral">Cheap gig</Badge> : null}
        </div>
        <h2 className="mt-3 font-display text-2xl font-black text-bone">{event.title}</h2>
        <p className="mt-1 text-sm leading-6 text-bone/62">
          {event.artist || "Artist TBC"} · {event.venue || "Venue TBC"} · {formatDate(event.starts_at)}
        </p>
        <p className="mt-2 text-sm text-bone/48">
          {event.price_min ? `From £${event.price_min}` : "Price TBC"} · {event.genre || "Live music"}
        </p>

        <div className="mt-5 grid gap-2 sm:grid-cols-3">
          {event.needs_review ? <ActionForm action={approveEventAction} eventId={event.id} label="Approve" tone="acid" /> : null}
          {event.status !== "rejected" ? <ActionForm action={rejectEventAction} eventId={event.id} label="Reject" tone="poster" /> : null}
          {!event.top_pick ? <ActionForm action={markTopPickAction} eventId={event.id} label="Mark top pick" tone="clyde" /> : null}
        </div>
      </div>

      <details className="rounded-md border border-bone/10 bg-night/70 p-4">
        <summary className="cursor-pointer text-sm font-black uppercase tracking-[0.14em] text-clyde">Edit</summary>
        <form action={updateEventAction} className="mt-4 space-y-3">
          <input type="hidden" name="eventId" value={event.id} />
          <input className="w-full rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone" name="title" defaultValue={event.title} />
          <input className="w-full rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone" name="starts_at" type="datetime-local" defaultValue={event.starts_at.slice(0, 16)} />
          <input className="w-full rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone" name="price" placeholder="Price" defaultValue={event.price_min ?? ""} />
          <input className="w-full rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone" name="ticket_url" placeholder="Ticket URL" defaultValue={event.ticket_url ?? ""} />
          <input className="w-full rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone" name="genre" placeholder="Genre" defaultValue={event.genre ?? ""} />
          <textarea className="min-h-20 w-full rounded-md border border-bone/10 bg-ink px-3 py-2 text-sm text-bone" name="notes" placeholder="Editorial note" defaultValue={event.editorial_note ?? ""} />
          <SubmitButton pendingText="Saving" className="w-full rounded-md border border-clyde px-3 py-2 text-sm font-black uppercase text-clyde">
            Save edit
          </SubmitButton>
        </form>
      </details>
    </article>
  );
}

function ActionForm({
  action,
  eventId,
  label,
  tone
}: {
  action: (formData: FormData) => Promise<void>;
  eventId: number;
  label: string;
  tone: "acid" | "poster" | "clyde";
}) {
  const tones = {
    acid: "bg-acid text-ink",
    poster: "bg-poster text-bone",
    clyde: "bg-clyde text-ink"
  };
  return (
    <form action={action}>
      <input type="hidden" name="eventId" value={eventId} />
      <SubmitButton pendingText="Working" className={`w-full rounded-md px-3 py-2 text-xs font-black uppercase ${tones[tone]}`}>
        {label}
      </SubmitButton>
    </form>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: "acid" | "poster" | "clyde" | "neutral" }) {
  const tones = {
    acid: "bg-acid text-ink",
    poster: "bg-poster text-bone",
    clyde: "bg-clyde text-ink",
    neutral: "bg-bone/10 text-bone/65"
  };
  return <span className={`rounded px-2 py-1 text-xs font-black uppercase tracking-[0.12em] ${tones[tone]}`}>{children}</span>;
}

function matchesFilter(event: AdminEvent, filter: Filter) {
  const date = new Date(event.starts_at);
  if (filter === "all") return true;
  if (filter === "needs review") return event.needs_review;
  if (filter === "approved") return !event.needs_review && event.status === "scheduled";
  if (filter === "top picks") return event.top_pick;
  if (filter === "cheap gigs") return cheapGig(event);
  if (filter === "hidden gems") return false;
  if (filter === "weekend") return [5, 6, 0].includes(date.getDay());
  if (filter === "this week") return isThisWeek(date);
  return true;
}

function cheapGig(event: AdminEvent) {
  const price = Number(event.price_min ?? event.price_max ?? Number.NaN);
  return Number.isFinite(price) && price <= 10;
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
