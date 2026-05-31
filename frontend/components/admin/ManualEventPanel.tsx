import { addManualEvent, uploadCsv } from "@/app/admin/actions";
import type { Venue } from "@/lib/types";

export function ManualEventPanel({ venues }: { venues: Venue[] }) {
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <form action={addManualEvent} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
        <h2 className="font-display text-2xl font-black text-bone">Add manual event</h2>
        <div className="mt-4 grid gap-3">
          <input name="title" required placeholder="Event / artist title" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <select name="venue_slug" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
            {venues.map((venue) => (
              <option key={venue.slug} value={venue.slug}>
                {venue.name}
              </option>
            ))}
          </select>
          <input name="starts_at" required type="datetime-local" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <input name="ticket_url" placeholder="Ticket link" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <input name="genre" placeholder="Genre" className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          <button className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
            Add event
          </button>
        </div>
      </form>
      <form action={uploadCsv} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
        <h2 className="font-display text-2xl font-black text-bone">Upload CSV</h2>
        <p className="mt-2 text-sm leading-6 text-bone/55">
          Required columns: `title`, `venue_name`, `starts_at`. Optional: `artist_name`,
          `ticket_url`, `genre`.
        </p>
        <input name="csv" required type="file" accept=".csv,text/csv" className="mt-5 w-full rounded-md border border-dashed border-bone/20 bg-night px-3 py-8 text-sm text-bone/65" />
        <button className="mt-4 rounded-md bg-clyde px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
          Import CSV
        </button>
      </form>
    </section>
  );
}
