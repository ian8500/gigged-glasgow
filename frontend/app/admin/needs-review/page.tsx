import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { EventBoard } from "@/components/admin/EventBoard";
import { getAdminEvents } from "@/lib/api";

export default async function NeedsReviewPage() {
  const events = await getAdminEvents("needs-review");
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Editorial workflow" title="Needs review" />
      <EventBoard events={events} mode="needs-review" />
    </main>
  );
}
