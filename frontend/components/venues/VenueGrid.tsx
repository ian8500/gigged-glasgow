import type { Venue } from "@/lib/types";

export function VenueGrid({ venues }: { venues: Venue[] }) {
  return (
    <main className="space-y-6">
      <div>
        <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Venues</p>
        <h1 className="mt-2 font-display text-5xl font-black text-bone">Glasgow whitelist</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {venues.map((venue) => (
          <article key={venue.id} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
            <h2 className="font-display text-xl font-black text-bone">{venue.name}</h2>
            <p className="mt-2 min-h-10 text-sm text-bone/60">
              {[venue.address, venue.postcode].filter(Boolean).join(", ")}
            </p>
            <div className="mt-5 flex items-center justify-between text-sm">
              <span className="text-bone/50">Capacity {venue.capacity ?? "TBC"}</span>
              <span className="font-bold text-clyde">{venue.instagram_handle ?? "No IG"}</span>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}

