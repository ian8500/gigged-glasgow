import { generateWeeklyRoundup } from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SubmitButton } from "@/components/admin/SubmitButton";
import { SocialPostPreview } from "@/components/social/SocialPostPreview";
import { getAdminEvents } from "@/lib/api";

export default async function WeeklyIssuePage() {
  const events = await getAdminEvents("approved");
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Issue builder" title="Weekly issue builder">
        <form action={generateWeeklyRoundup}>
          <SubmitButton pendingText="Running" className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
            Generate weekly roundup
          </SubmitButton>
        </form>
      </AdminPageHeader>
      <section className="grid gap-5 lg:grid-cols-[1fr_380px]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Approved event pool</h2>
          <p className="mt-2 text-sm text-bone/55">
            Generating a weekly issue first runs the Glasgow venue coverage checks, records a coverage report, and flags gaps before ranking events.
          </p>
          <div className="mt-5 divide-y divide-bone/10">
            {events.map((event) => (
              <div key={event.id} className="py-3">
                <div className="font-black text-bone">{event.artist}</div>
                <div className="text-sm text-bone/55">{event.venue} · {event.starts_at.slice(0, 10)}</div>
              </div>
            ))}
          </div>
        </div>
        <SocialPostPreview templateKey="weekly-roundup" />
      </section>
    </main>
  );
}
