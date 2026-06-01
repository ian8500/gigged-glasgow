import { WeeklyBuilder } from "@/components/weekly/WeeklyBuilder";
import { getAdminEvents } from "@/lib/api";

export default async function WeeklyPage() {
  const events = await getAdminEvents("approved");
  return <WeeklyBuilder events={events} />;
}
