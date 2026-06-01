import { AddGigForm } from "@/components/events/AddGigForm";
import { getVenues } from "@/lib/api";

export default async function NewEventPage({
  searchParams
}: {
  searchParams: { venue?: string };
}) {
  const venues = await getVenues();

  return (
    <main className="space-y-6">
      <header>
        <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Add Gig Manually</p>
        <h1 className="mt-2 font-display text-4xl font-black leading-none text-bone md:text-5xl">New gig</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/58">
          Manual entry is the primary workflow. API imports are optional future automation and are not required.
        </p>
      </header>
      <AddGigForm selectedVenue={searchParams.venue} venues={venues} />
    </main>
  );
}
