import {
  approveEvent,
  editEvent,
  markSponsored,
  markTopPick,
  mergeDuplicateEvents,
  rejectEvent
} from "@/app/admin/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { AdminEvent } from "@/lib/types";

export function EventBoard({ events, mode }: { events: AdminEvent[]; mode: string }) {
  return (
    <section className="space-y-4">
      {events.length === 0 ? (
        <div className="rounded-lg border border-dashed border-bone/20 bg-bone/[0.03] p-10 text-bone/55">
          No events in this view yet.
        </div>
      ) : (
        events.map((event) => <EventCard key={event.id} event={event} allEvents={events} mode={mode} />)
      )}
    </section>
  );
}

function EventCard({
  event,
  allEvents,
  mode
}: {
  event: AdminEvent;
  allEvents: AdminEvent[];
  mode: string;
}) {
  return (
    <article className="grid gap-4 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 lg:grid-cols-[1fr_360px]">
      <div>
        <div className="flex flex-wrap gap-2">
          {event.needs_review ? <Badge tone="poster">Needs review</Badge> : <Badge tone="clyde">Approved</Badge>}
          {event.top_pick ? <Badge tone="acid">Top pick</Badge> : null}
          {event.sponsored ? <Badge tone="plum">Sponsored</Badge> : null}
          <Badge tone="neutral">{Math.round(event.confidence_score * 100)}% confidence</Badge>
        </div>
        <h2 className="mt-3 font-display text-2xl font-black text-bone">{event.title}</h2>
        <p className="mt-1 text-bone/62">
          {event.artist} · {event.venue} ·{" "}
          {new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(
            new Date(event.starts_at)
          )}
        </p>
        <p className="mt-3 text-sm text-bone/45">Internal source: {event.source_attribution}</p>

        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          <ActionForm action={approveEvent} eventId={event.id} label="Approve" tone="acid" />
          <ActionForm action={rejectEvent} eventId={event.id} label="Reject" tone="poster" />
          <ActionForm action={markTopPick} eventId={event.id} label="Top pick" tone="clyde" />
          <ActionForm action={markSponsored} eventId={event.id} label="Sponsored" tone="plum" />
        </div>

        <form action={mergeDuplicateEvents} className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input type="hidden" name="keeperId" value={event.id} />
          <select name="duplicateId" className="min-w-0 flex-1 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone">
            {allEvents
              .filter((candidate) => candidate.id !== event.id)
              .map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  Merge duplicate: {candidate.title} at {candidate.venue}
                </option>
              ))}
          </select>
          <SubmitButton pendingText="Merging" className="rounded-md border border-bone/15 px-3 py-2 text-sm font-black uppercase tracking-[0.12em] text-bone/75">
            Merge
          </SubmitButton>
        </form>
      </div>

      <form action={editEvent} className="space-y-3">
        <input type="hidden" name="eventId" value={event.id} />
        <input name="title" defaultValue={event.title} className="w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
        <input name="starts_at" defaultValue={event.starts_at.slice(0, 16)} type="datetime-local" className="w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
        <input name="ticket_url" defaultValue={event.ticket_url ?? ""} placeholder="Ticket link" className="w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
        <input name="genre" defaultValue={event.genre ?? ""} placeholder="Genre" className="w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
        <textarea name="editorial_note" defaultValue={event.editorial_note ?? ""} placeholder="Short punchy description or editor note" className="h-24 w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
        <SubmitButton pendingText="Saving" className="w-full rounded-md border border-clyde px-3 py-2 text-sm font-black uppercase tracking-[0.14em] text-clyde">
          Save event
        </SubmitButton>
      </form>
    </article>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: string }) {
  const tones: Record<string, string> = {
    acid: "bg-acid text-ink",
    clyde: "bg-clyde text-ink",
    poster: "bg-poster text-bone",
    plum: "bg-plum text-bone",
    neutral: "bg-bone/10 text-bone/65"
  };
  return <span className={`rounded px-2 py-1 text-xs font-black uppercase tracking-[0.12em] ${tones[tone]}`}>{children}</span>;
}

function ActionForm({
  action,
  eventId,
  label,
  tone
}: {
  action: (formData: FormData) => Promise<void>;
  eventId: number;
  label: string;
  tone: string;
}) {
  const tones: Record<string, string> = {
    acid: "bg-acid text-ink",
    clyde: "bg-clyde text-ink",
    poster: "bg-poster text-bone",
    plum: "bg-plum text-bone"
  };
  return (
    <form action={action}>
      <input type="hidden" name="eventId" value={eventId} />
      <SubmitButton pendingText="Working" className={`w-full rounded-md px-3 py-2 text-xs font-black uppercase ${tones[tone]}`}>
        {label}
      </SubmitButton>
    </form>
  );
}
