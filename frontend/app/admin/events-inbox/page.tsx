import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { EventBoard } from "@/components/admin/EventBoard";
import { ManualEventPanel } from "@/components/admin/ManualEventPanel";
import { getAdminEvents, getVenues } from "@/lib/api";

export default async function EventsInboxPage() {
  const [events, venues] = await Promise.all([getAdminEvents("inbox"), getVenues()]);
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Inbox" title="Events inbox" />
      <ManualEventPanel venues={venues} />
      <EventBoard events={events} mode="inbox" />
    </main>
  );
}
