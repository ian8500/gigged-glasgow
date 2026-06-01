import { getDashboard, getEvents, getSocialPosts, getVenues } from "@/lib/api";

const quickLinks = [
  { href: "/venues", label: "Open Venue Watchlist", description: "Check venue pages and add gigs." },
  { href: "/events/new", label: "Add Gig", description: "Create a manual gig listing." },
  { href: "/events", label: "Review Events", description: "Approve, reject, and filter gigs." },
  { href: "/weekly", label: "Build Weekly Issue", description: "Draft copy from approved gigs." }
];

export default async function HomePage() {
  const [dashboard, events, venues, posts] = await Promise.all([
    getDashboard(),
    getEvents(),
    getVenues(),
    getSocialPosts()
  ]);

  const upcoming = events.filter((event) => new Date(event.starts_at).getTime() >= Date.now()).length;
  const needsReview = events.filter((event) => event.needs_review || event.status === "review").length;

  return (
    <main className="space-y-8">
      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6 shadow-poster md:p-8">
        <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Manual gig desk</p>
        <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_320px] lg:items-end">
          <div>
            <h1 className="font-display text-4xl font-black leading-none text-bone md:text-6xl">
              Gigged Glasgow
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-bone/68">
              Venue check, add gig, approve gig, generate weekly copy, then export for manual Instagram posting.
              Works without API keys; backend data improves it when available.
            </p>
          </div>
          <div className="rounded-md border border-clyde/30 bg-clyde/10 p-4 text-sm leading-6 text-bone/75">
            <strong className="block text-clyde">Backend status</strong>
            {venues.length || events.length || posts.length || dashboard.counts.venues ? (
              "Connected or using cached seeded data."
            ) : (
              "Backend unavailable or empty. Run backend then refresh, or start by seeding venues."
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="Venues" value={dashboard.counts.venues || venues.length} />
        <Stat label="Upcoming gigs" value={dashboard.counts.events || upcoming} />
        <Stat label="Needs review" value={dashboard.counts.needs_review || needsReview} />
        <Stat label="Generated posts" value={dashboard.counts.social_posts || posts.length} />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {quickLinks.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className="rounded-lg border border-bone/10 bg-night/80 p-5 transition hover:border-acid/60 hover:bg-bone/[0.06]"
          >
            <span className="font-display text-xl font-black text-bone">{link.label}</span>
            <span className="mt-3 block text-sm leading-6 text-bone/55">{link.description}</span>
          </a>
        ))}
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <h2 className="font-display text-2xl font-black text-bone">Next gigs</h2>
            <p className="mt-1 text-sm text-bone/50">A quick read of what is already in the queue.</p>
          </div>
          <a className="rounded-md border border-clyde px-4 py-2 text-sm font-black uppercase text-clyde" href="/events">
            Open Events
          </a>
        </div>
        <div className="mt-5 divide-y divide-bone/10">
          {events.slice(0, 6).length ? (
            events.slice(0, 6).map((event) => (
              <div key={event.id} className="grid gap-2 py-4 md:grid-cols-[1fr_180px]">
                <div>
                  <p className="font-bold text-bone">{event.title}</p>
                  <p className="mt-1 text-sm text-bone/55">{event.venue?.name ?? "Venue TBC"}</p>
                </div>
                <p className="text-sm font-semibold text-acid md:text-right">{formatDate(event.starts_at)}</p>
              </div>
            ))
          ) : (
            <div className="rounded-md border border-dashed border-bone/15 p-6 text-sm text-bone/55">
              No gigs yet. Add one manually or run backend then refresh.
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-bone/45">{label}</p>
      <p className="mt-3 font-display text-4xl font-black text-acid">{value}</p>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date TBC";
  }
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
