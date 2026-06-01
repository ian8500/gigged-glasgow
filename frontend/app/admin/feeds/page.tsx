import { createFeed, deleteFeed, disableFeed, runFeed, testFeed } from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SubmitButton } from "@/components/admin/SubmitButton";
import { getFeeds } from "@/lib/api";

export default async function FeedsPage() {
  const feeds = await getFeeds();

  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Sources" title="Feeds" />
      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
        <form action={createFeed} className="grid gap-3 lg:grid-cols-[180px_1fr_120px_1fr_160px]">
          <input name="source_name" placeholder="Source name" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <input name="feed_url" placeholder="RSS, Atom or iCal URL" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <select name="feed_type" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
            <option value="rss">RSS</option>
            <option value="atom">Atom</option>
            <option value="ical">iCal</option>
          </select>
          <input name="notes" placeholder="Notes" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <SubmitButton pendingText="Adding" className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
            Add feed
          </SubmitButton>
        </form>
      </section>

      <section className="grid gap-4">
        {feeds.map((feed) => (
          <div key={feed.id} className="grid gap-4 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 lg:grid-cols-[1fr_220px]">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-display text-xl font-black text-bone">{feed.source_name}</h2>
                <span className="rounded bg-bone/10 px-3 py-1 text-xs font-black uppercase tracking-[0.14em] text-clyde">{feed.feed_type}</span>
                <span className={`rounded px-3 py-1 text-xs font-black uppercase tracking-[0.14em] ${feed.enabled ? "bg-clyde text-ink" : "bg-bone/10 text-bone/45"}`}>
                  {feed.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <p className="mt-3 break-all text-sm text-bone/60">{feed.feed_url}</p>
              <p className="mt-2 text-xs text-bone/45">Last checked: {feed.last_checked_at ?? "never"} · Last success: {feed.last_success_at ?? "never"}</p>
              {feed.last_error ? <p className="mt-2 text-xs text-poster">{feed.last_error}</p> : null}
            </div>
            <div className="space-y-3">
              <FeedAction feedId={feed.id} action={testFeed} label="Test feed" />
              <FeedAction feedId={feed.id} action={runFeed} label="Run feed" />
              <FeedAction feedId={feed.id} action={disableFeed} label="Disable feed" />
              <FeedAction feedId={feed.id} action={deleteFeed} label="Delete feed" />
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}

function FeedAction({ feedId, action, label }: { feedId: number; action: (formData: FormData) => Promise<void>; label: string }) {
  return (
    <form action={action}>
      <input type="hidden" name="feedId" value={feedId} />
      <SubmitButton pendingText="Working" className="w-full rounded-md border border-bone/20 px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-bone">
        {label}
      </SubmitButton>
    </form>
  );
}
