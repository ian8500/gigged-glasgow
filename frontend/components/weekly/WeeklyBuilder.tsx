"use client";

import { useMemo, useState } from "react";

import type { AdminEvent } from "@/lib/types";

type Mode = "weekly" | "weekend" | "cheap" | "hidden";

const buttons: Array<{ mode: Mode; label: string }> = [
  { mode: "weekly", label: "Generate Weekly Issue" },
  { mode: "weekend", label: "Generate Weekend Picks" },
  { mode: "cheap", label: "Generate Cheap Gigs" },
  { mode: "hidden", label: "Generate Hidden Gem" }
];

export function WeeklyBuilder({ events }: { events: AdminEvent[] }) {
  const [mode, setMode] = useState<Mode>("weekly");
  const selected = useMemo(() => selectEvents(events, mode), [events, mode]);
  const preview = buildPreview(selected, mode);

  return (
    <main className="space-y-6">
      <header>
        <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Weekly Issue Builder</p>
        <h1 className="mt-2 font-display text-4xl font-black leading-none text-bone md:text-5xl">Build the guide</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/58">
          Frontend-only preview builder from approved gigs. It stays useful even when backend generation is unavailable.
        </p>
      </header>

      <section className="grid gap-4 lg:grid-cols-[1fr_420px]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <h2 className="font-display text-2xl font-black text-bone">Approved gigs this week</h2>
            <span className="rounded bg-bone/10 px-3 py-1 text-sm text-bone/62">{events.length} approved</span>
          </div>
          <div className="mt-5 divide-y divide-bone/10">
            {events.length ? (
              events.map((event) => (
                <div key={event.id} className="grid gap-2 py-4 md:grid-cols-[1fr_160px]">
                  <div>
                    <p className="font-bold text-bone">{event.title}</p>
                    <p className="mt-1 text-sm text-bone/55">
                      {event.artist || "Artist TBC"} · {event.venue || "Venue TBC"}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-acid md:text-right">{formatDate(event.starts_at)}</p>
                </div>
              ))
            ) : (
              <p className="rounded-md border border-dashed border-bone/15 p-6 text-sm text-bone/55">
                No approved gigs yet. Approve gigs in Events Review, or run backend then refresh.
              </p>
            )}
          </div>
        </div>

        <aside className="rounded-lg border border-bone/10 bg-night/80 p-5">
          <h2 className="font-display text-2xl font-black text-bone">Selected gigs</h2>
          <div className="mt-4 grid gap-2">
            {buttons.map((button) => (
              <button
                key={button.mode}
                className={`rounded-md px-3 py-2 text-left text-xs font-black uppercase ${
                  mode === button.mode ? "bg-acid text-ink" : "border border-bone/15 text-bone/65"
                }`}
                onClick={() => setMode(button.mode)}
                type="button"
              >
                {button.label}
              </button>
            ))}
          </div>

          <textarea
            className="mt-5 min-h-96 w-full rounded-md border border-bone/10 bg-ink p-4 text-sm leading-6 text-bone"
            readOnly
            value={preview}
          />
          <button
            className="mt-3 w-full rounded-md bg-clyde px-4 py-3 text-sm font-black uppercase text-ink"
            onClick={() => navigator.clipboard.writeText(preview)}
            type="button"
          >
            Copy preview
          </button>
        </aside>
      </section>
    </main>
  );
}

function selectEvents(events: AdminEvent[], mode: Mode) {
  const thisWeek = events.filter((event) => isThisWeek(new Date(event.starts_at)));
  if (mode === "weekend") {
    return thisWeek.filter((event) => [5, 6, 0].includes(new Date(event.starts_at).getDay())).slice(0, 6);
  }
  if (mode === "cheap") {
    return thisWeek.filter((event) => {
      const price = Number(event.price_min ?? event.price_max ?? Number.NaN);
      return Number.isFinite(price) && price <= 10;
    });
  }
  if (mode === "hidden") {
    return thisWeek.filter((event) => !event.top_pick).slice(0, 1);
  }
  return thisWeek.slice(0, 10);
}

function buildPreview(events: AdminEvent[], mode: Mode) {
  const title = {
    weekly: "Gigged Glasgow weekly picks",
    weekend: "Gigged Glasgow weekend picks",
    cheap: "Cheap gigs in Glasgow this week",
    hidden: "Hidden gem gig"
  }[mode];

  if (!events.length) {
    return `${title}\n\nNo matching approved gigs yet.\n\nApprove gigs in Events Review, then come back here.`;
  }

  return [
    title,
    "",
    ...events.map((event) => {
      const price = event.price_min ? ` · from £${event.price_min}` : "";
      return `- ${event.title} · ${event.venue || "Venue TBC"} · ${formatDate(event.starts_at)}${price}`;
    }),
    "",
    "#GiggedGlasgow #GlasgowGigs #GlasgowMusic"
  ].join("\n");
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
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
