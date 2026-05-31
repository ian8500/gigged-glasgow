import { EventList } from "@/components/events/EventList";
import { getEvents } from "@/lib/api";

export default async function EventsPage() {
  const events = await getEvents();
  return <EventList events={events} />;
}

