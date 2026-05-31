import type { Event } from "@/lib/types";

export function EventList({ events }: { events: Event[] }) {
  return (
    <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-2xl font-black text-bone">Upcoming gigs</h2>
        <span className="rounded bg-bone/10 px-3 py-1 text-sm text-bone/70">
          {events.length} events
        </span>
      </div>

      <div className="mt-5 divide-y divide-bone/10">
        {events.length === 0 ? (
          <div className="py-10 text-bone/55">
            No events yet. Seed venues, then add events through the admin API.
          </div>
        ) : (
          events.map((event) => (
            <article key={event.id} className="grid gap-3 py-4 md:grid-cols-[1fr_180px]">
              <div>
                <h3 className="font-display text-xl font-black text-bone">{event.title}</h3>
                <p className="mt-1 text-sm text-bone/60">
                  {event.venue?.name ?? "Venue TBC"} · {event.genre ?? "Live music"}
                </p>
              </div>
              <div className="text-left md:text-right">
                <p className="font-semibold text-acid">
                  {new Intl.DateTimeFormat("en-GB", {
                    dateStyle: "medium",
                    timeStyle: "short"
                  }).format(new Date(event.starts_at))}
                </p>
                {event.needs_review ? (
                  <p className="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-poster">
                    Needs review
                  </p>
                ) : null}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

