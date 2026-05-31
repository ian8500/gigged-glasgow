import { getDashboard, getEvents, getVenues } from "@/lib/api";
import { StatCard } from "@/components/admin/StatCard";
import { EventList } from "@/components/events/EventList";
import { PostPreview } from "@/components/admin/PostPreview";
import { SocialTemplateGrid } from "@/components/social/SocialTemplateGrid";

export default async function HomePage() {
  const [dashboard, events, venues] = await Promise.all([
    getDashboard(),
    getEvents(),
    getVenues()
  ]);

  return (
    <main className="space-y-8">
      <section className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-8 shadow-poster">
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">
            Your weekly Glasgow gig radar.
          </p>
          <h1 className="mt-4 max-w-3xl font-display text-5xl font-black leading-[0.95] text-bone md:text-7xl">
            Gigged Glasgow
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-bone/72">
            A city-based live music desk for discovering upcoming gigs, managing venue data,
            and preparing Instagram-ready weekly posts for Glasgow.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {["Useful", "Local", "Music-first"].map((item) => (
              <div key={item} className="border-l-4 border-acid bg-ink/35 px-4 py-3">
                <p className="font-display text-xl font-black uppercase text-bone">{item}</p>
              </div>
            ))}
          </div>
        </div>
        <PostPreview templateKey="weekly-roundup" />
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Events" value={dashboard.counts.events} tone="acid" />
        <StatCard label="Venues" value={dashboard.counts.venues || venues.length} tone="clyde" />
        <StatCard label="Posts" value={dashboard.counts.social_posts} tone="poster" />
        <StatCard label="Needs review" value={dashboard.counts.needs_review} tone="plum" />
      </section>

      <EventList events={events} />
      <SocialTemplateGrid />
    </main>
  );
}
