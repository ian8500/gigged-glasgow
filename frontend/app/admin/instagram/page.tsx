import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { getInstagramSettings, getSocialReviewQueue } from "@/lib/api";

export default async function InstagramSettingsPage() {
  const [settings, approvedPosts, scheduledPosts] = await Promise.all([
    getInstagramSettings(),
    getSocialReviewQueue("approved"),
    getSocialReviewQueue("scheduled")
  ]);

  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Publishing prep" title="Instagram account settings" />

      <section className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">
            Official API readiness
          </p>
          <h2 className="mt-3 font-display text-3xl font-black text-bone">
            {settings.ready ? "Meta credentials configured" : "Manual export mode"}
          </h2>
          <p className="mt-3 text-sm leading-6 text-bone/62">{settings.reason}</p>
          <div className="mt-5 rounded-md border border-clyde/30 bg-clyde/10 p-4 text-sm leading-6 text-bone/70">
            Required account type: {settings.account_type}
          </div>
        </div>

        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <p className="font-display text-sm uppercase tracking-[0.24em] text-clyde">
            Environment variables
          </p>
          <div className="mt-4 grid gap-2 text-sm text-bone/68">
            {[
              "META_APP_ID",
              "META_APP_SECRET",
              "META_ACCESS_TOKEN",
              "INSTAGRAM_BUSINESS_ACCOUNT_ID",
              "META_GRAPH_API_VERSION",
              "META_PUBLISHING_ENABLED"
            ].map((item) => (
              <code key={item} className="rounded bg-ink/45 px-3 py-2">
                {item}
              </code>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Required permissions</h2>
          <ul className="mt-4 space-y-2 text-sm text-bone/65">
            {settings.required_permissions.map((permission) => (
              <li key={permission} className="rounded bg-bone/[0.04] px-3 py-2">
                {permission}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Safe fallback</h2>
          <p className="mt-3 text-sm leading-6 text-bone/65">{settings.safe_fallback}</p>
          <p className="mt-4 text-sm leading-6 text-bone/50">
            Approved and scheduled posts remain local. Use the exported PNG paths and scheduling
            JSON from the review queue for manual posting or an approved scheduler.
          </p>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Approved exports</h2>
          <p className="mt-2 text-sm text-bone/55">{approvedPosts.length} posts ready to schedule.</p>
        </div>
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Scheduled locally</h2>
          <p className="mt-2 text-sm text-bone/55">{scheduledPosts.length} posts prepared for manual posting.</p>
        </div>
      </section>
    </main>
  );
}
