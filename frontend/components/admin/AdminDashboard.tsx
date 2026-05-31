import { PostPreview } from "@/components/admin/PostPreview";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SocialReviewQueue } from "@/components/admin/SocialReviewQueue";
import { StatCard } from "@/components/admin/StatCard";
import { SocialTemplateGrid } from "@/components/social/SocialTemplateGrid";
import type { DashboardSummary, SocialPost, Venue } from "@/lib/types";

export function AdminDashboard({
  dashboard,
  venues,
  reviewPosts
}: {
  dashboard: DashboardSummary;
  venues: Venue[];
  reviewPosts: SocialPost[];
}) {
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Admin" title="Glasgow radar desk">
        <a
          href="/venues"
          className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink"
        >
          Manage venues
        </a>
      </AdminPageHeader>

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Events" value={dashboard.counts.events} tone="acid" />
        <StatCard label="Venues" value={dashboard.counts.venues || venues.length} tone="clyde" />
        <StatCard label="Posts" value={dashboard.counts.social_posts} tone="poster" />
        <StatCard label="Review" value={dashboard.counts.needs_review} tone="plum" />
      </section>

      <section className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <div className="flex items-center justify-between gap-4">
            <h2 className="font-display text-2xl font-black text-bone">Venue whitelist</h2>
            <span className="rounded bg-bone/10 px-3 py-1 text-sm text-bone/70">
              {venues.length} seeded
            </span>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {venues.map((venue) => (
              <div
                key={venue.id}
                className="rounded-md border border-bone/10 bg-ink/30 p-4"
              >
                <div className="font-display text-lg font-black text-bone">{venue.name}</div>
                <div className="mt-1 text-sm text-bone/55">{venue.address}</div>
                <div className="mt-3 text-xs font-bold uppercase tracking-[0.16em] text-clyde">
                  {venue.is_whitelisted ? "Whitelisted" : "Unlisted"}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-5">
          <PostPreview templateKey="tonight" />
          <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
            <p className="font-display text-sm uppercase tracking-[0.22em] text-acid">
              Brand rule
            </p>
            <p className="mt-3 text-sm leading-6 text-bone/65">
              Lead with the useful detail: date, venue, price, then taste. Keep the city voice
              sharp and direct.
            </p>
          </div>
        </div>
      </section>
      <SocialReviewQueue posts={reviewPosts} />
      <SocialTemplateGrid />
    </main>
  );
}
