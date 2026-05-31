import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { EventBoard } from "@/components/admin/EventBoard";
import { getAdminEvents } from "@/lib/api";

export default async function ApprovedEventsPage() {
  const events = await getAdminEvents("approved");
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Ready to publish" title="Approved events" />
      <EventBoard events={events} mode="approved" />
    </main>
  );
}
