import { VenueGrid } from "@/components/venues/VenueGrid";
import { getVenues } from "@/lib/api";

export default async function VenuesPage() {
  const venues = await getVenues();
  return <VenueGrid venues={venues} />;
}

