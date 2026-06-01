"use client";

import { useState, useTransition } from "react";

import {
  approveScrapeCandidateAction,
  convertScrapeCandidateAction,
  rejectScrapeCandidateAction,
  runCityScrapeAction
} from "@/app/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { ExtractedEventCandidate, ScrapeStatus } from "@/lib/types";

export function AutoFinderClient({
  status,
  candidates
}: {
  status: ScrapeStatus;
  candidates: ExtractedEventCandidate[];
}) {
  const [message, setMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  function runScrape() {
    startTransition(async () => {
      const result = await runCityScrapeAction();
      setMessage(result.message);
    });
  }

  return (
    <main className="space-y-6">
      <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Auto Finder</p>
          <h1 className="mt-2 font-display text-4xl font-black leading-none text-bone md:text-5xl">
            Safe venue-page gig finder
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/58">
            Checks only official venue event pages stored in the venue database. Extracted gigs stay in review until approved and converted.
          </p>
        </div>
        <button
          className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase text-ink disabled:opacity-50"
          disabled={isPending}
          onClick={runScrape}
          type="button"
        >
          {isPending ? "Running" : "Run city scrape"}
        </button>
      </header>

      {message ? <p className="rounded-md border border-clyde/25 bg-clyde/10 px-4 py-3 text-sm text-clyde">{message}</p> : null}

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="Venues checked" value={status.venues_checked} />
        <Stat label="Events found" value={status.events_found} />
        <Stat label="Need review" value={status.candidates_needing_review ?? status.events_needing_review} />
        <Stat label="Run status" value={status.status} text />
      </section>

      {(status.errors.length || status.warnings.length) ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <Diagnostics title="Errors" items={status.errors} tone="poster" />
          <Diagnostics title="Warnings" items={status.warnings} tone="amber" />
        </section>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <h2 className="font-display text-2xl font-black text-bone">Extracted candidates</h2>
          <span className="rounded bg-bone/10 px-3 py-1 text-sm text-bone/62">{candidates.length} total</span>
        </div>
        {candidates.length ? (
          candidates.map((candidate) => <CandidateCard key={candidate.id} candidate={candidate} />)
        ) : (
          <div className="rounded-lg border border-dashed border-bone/20 bg-bone/[0.03] p-8 text-sm text-bone/58">
            No extracted candidates yet. Run Auto Finder or keep using the manual workflow.
          </div>
        )}
      </section>
    </main>
  );
}

function CandidateCard({ candidate }: { candidate: ExtractedEventCandidate }) {
  return (
    <article className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge>{candidate.status}</Badge>
            <Badge>{candidate.source_type}</Badge>
            <Badge>{Math.round(candidate.confidence_score * 100)}% confidence</Badge>
          </div>
          <h3 className="mt-3 font-display text-2xl font-black text-bone">{candidate.title}</h3>
          <p className="mt-1 text-sm leading-6 text-bone/62">
            {candidate.venue_name ?? "Venue TBC"} · {formatDate(candidate.starts_at)} · {candidate.price_text ?? "Price TBC"}
          </p>
          <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
            <Meta label="Ticket URL" value={candidate.ticket_url} />
            <Meta label="Source URL" value={candidate.source_url} />
          </div>
        </div>

        <div className="grid h-fit gap-2">
          <ActionForm action={approveScrapeCandidateAction} candidateId={candidate.id} label="Approve" disabled={candidate.status === "approved"} />
          <ActionForm action={rejectScrapeCandidateAction} candidateId={candidate.id} label="Reject" disabled={candidate.status === "rejected"} />
          <ActionForm action={convertScrapeCandidateAction} candidateId={candidate.id} label="Convert to event" disabled={candidate.status === "rejected"} />
          {candidate.source_url ? (
            <a className="rounded-md border border-bone/15 px-3 py-2 text-center text-xs font-black uppercase text-bone/70" href={candidate.source_url} rel="noreferrer" target="_blank">
              Open source page
            </a>
          ) : null}
          <details className="rounded-md border border-bone/10 p-3">
            <summary className="cursor-pointer text-xs font-black uppercase text-clyde">View diagnostic note</summary>
            <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap text-xs leading-5 text-bone/55">
              {JSON.stringify(candidate.raw_payload ?? {}, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    </article>
  );
}

function ActionForm({
  action,
  candidateId,
  label,
  disabled
}: {
  action: (formData: FormData) => Promise<void>;
  candidateId: number;
  label: string;
  disabled?: boolean;
}) {
  return (
    <form action={action}>
      <input type="hidden" name="candidateId" value={candidateId} />
      <SubmitButton
        pendingText="Working"
        className="w-full rounded-md border border-clyde px-3 py-2 text-xs font-black uppercase text-clyde"
        disabled={disabled}
      >
        {label}
      </SubmitButton>
    </form>
  );
}

function Stat({ label, value, text }: { label: string; value: number | string; text?: boolean }) {
  return (
    <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-bone/40">{label}</p>
      <p className={`mt-3 font-display font-black text-acid ${text ? "text-2xl" : "text-4xl"}`}>{value}</p>
    </div>
  );
}

function Diagnostics({ title, items, tone }: { title: string; items: string[]; tone: "poster" | "amber" }) {
  const colour = tone === "poster" ? "text-poster border-poster/25 bg-poster/10" : "text-amber border-amber/25 bg-amber/10";
  return (
    <div className={`rounded-lg border p-4 ${colour}`}>
      <h2 className="font-display text-xl font-black">{title}</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <p className="text-xs font-black uppercase tracking-[0.16em] text-bone/35">{label}</p>
      <p className="mt-1 break-words text-bone/70">{value || "Not set"}</p>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded bg-bone/10 px-2 py-1 text-xs font-black uppercase tracking-[0.12em] text-bone/65">{children}</span>;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Date TBC";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
