import { EventList } from "@/components/events/EventList";
import { getAdminEvents } from "@/lib/api";

export default async function EventsPage() {
  const events = await getAdminEvents("inbox");
  return <EventList events={events} />;
}
