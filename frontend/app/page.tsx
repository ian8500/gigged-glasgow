import { getDashboard, getEvents, getSocialPosts, getVenues } from "@/lib/api";
import { StatCard } from "@/components/admin/StatCard";
import { EventList } from "@/components/events/EventList";
import { PostPreview } from "@/components/admin/PostPreview";
import { SocialTemplateGrid } from "@/components/social/SocialTemplateGrid";

const quickLinks = [
  { href: "/venues", label: "Open Venue Watchlist", description: "Check venue pages and add gigs." },
  { href: "/events/new", label: "Add Gig", description: "Create a manual gig listing." },
  { href: "/events", label: "Browse Events", description: "Check the public Glasgow gig list." },
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
      <section className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6 shadow-poster md:p-8">
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Your weekly Glasgow gig radar</p>
          <h1 className="mt-4 max-w-3xl font-display text-4xl font-black leading-none text-bone md:text-6xl">
            Gigged Glasgow
          </h1>
          <p className="mt-5 max-w-3xl text-base leading-7 text-bone/68 md:text-lg md:leading-8">
            A city-based live music desk for discovering upcoming gigs, managing venue sources,
            and preparing Instagram-ready weekly posts for Glasgow.
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {["Useful", "Local", "Music-led"].map((item) => (
              <div key={item} className="border-l-4 border-acid bg-ink/35 px-4 py-3">
                <p className="font-display text-lg font-black uppercase text-bone md:text-xl">{item}</p>
              </div>
            ))}
          </div>
        </div>
        <PostPreview templateKey="weekly-roundup" compact />
      </section>

      <section className="rounded-lg border border-clyde/20 bg-clyde/10 p-4 text-sm leading-6 text-bone/75">
        <strong className="block text-clyde">Backend status</strong>
        {venues.length || events.length || posts.length || dashboard.counts.venues ? (
          "Connected or using cached seeded data."
        ) : (
          "Backend unavailable or empty. Run backend then refresh, or start by seeding venues."
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Venues" value={dashboard.counts.venues || venues.length} tone="clyde" />
        <StatCard label="Upcoming gigs" value={dashboard.counts.events || upcoming} tone="acid" />
        <StatCard label="Needs review" value={dashboard.counts.needs_review || needsReview} tone="plum" />
        <StatCard label="Posts" value={dashboard.counts.social_posts || posts.length} tone="poster" />
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

      <EventList events={events} />
      <SocialTemplateGrid />
    </main>
  );
}
