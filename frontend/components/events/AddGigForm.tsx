"use client";

import { useEffect, useRef } from "react";
import { useFormState } from "react-dom";
import { useRouter } from "next/navigation";

import { createGigAction, type ActionState } from "@/app/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { Venue } from "@/lib/types";

const initialState: ActionState = { ok: false, message: "" };

export function AddGigForm({ venues, selectedVenue }: { venues: Venue[]; selectedVenue?: string }) {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction] = useFormState(createGigAction, initialState);

  useEffect(() => {
    if (!state.ok) {
      return;
    }
    if (state.intent === "add-another") {
      formRef.current?.reset();
      return;
    }
    router.push("/events");
  }, [router, state]);

  return (
    <form ref={formRef} action={formAction} className="grid gap-5 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 md:grid-cols-2">
      <Field label="Event title" name="title" required />
      <Field label="Artist" name="artist" />

      <label className="grid gap-2 text-sm font-bold text-bone/70">
        Venue
        <select
          className="rounded-md border border-bone/10 bg-night px-3 py-3 text-sm text-bone"
          defaultValue={selectedVenue ?? ""}
          name="venue_slug"
          required
        >
          <option value="" disabled>
            Choose venue
          </option>
          {venues.map((venue) => (
            <option key={venue.id} value={venue.slug}>
              {venue.name}
            </option>
          ))}
        </select>
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Date" name="date" type="date" required />
        <Field label="Time" name="time" type="time" />
      </div>

      <Field label="Price" name="price" placeholder="Free, £8, £12.50" />
      <Field label="Ticket URL" name="ticket_url" type="url" />
      <Field label="Image URL" name="image_url" type="url" />
      <Field label="Genre" name="genre" />

      <label className="grid gap-2 text-sm font-bold text-bone/70 md:col-span-2">
        Notes
        <textarea
          className="min-h-28 rounded-md border border-bone/10 bg-night px-3 py-3 text-sm text-bone"
          name="notes"
          placeholder="Internal curation note, support acts, doors info, why it matters"
        />
      </label>

      <div className="flex flex-wrap gap-3 md:col-span-2">
        <Checkbox name="top_pick" label="Top pick" />
        <Checkbox name="hidden_gem" label="Hidden gem" />
        <Checkbox name="cheap_gig" label="Cheap gig" />
      </div>

      <div className="flex flex-col gap-3 border-t border-bone/10 pt-5 md:col-span-2 md:flex-row md:items-center md:justify-between">
        <p className={`min-h-5 text-sm font-semibold ${state.message ? (state.ok ? "text-clyde" : "text-poster") : "text-bone/45"}`}>
          {state.message || (venues.length ? "Save a manual gig to the review queue." : "No venues yet. Run backend then refresh.")}
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <a className="rounded-md border border-bone/15 px-4 py-3 text-center text-sm font-black uppercase text-bone/70" href="/events">
            Cancel
          </a>
          <SubmitButton
            pendingText="Saving"
            className="rounded-md border border-clyde px-4 py-3 text-sm font-black uppercase text-clyde"
            disabled={!venues.length}
          >
            <span>Save gig</span>
          </SubmitButton>
          <button
            className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase text-ink disabled:cursor-not-allowed disabled:opacity-55"
            disabled={!venues.length}
            name="intent"
            type="submit"
            value="add-another"
          >
            Save and add another
          </button>
        </div>
      </div>
    </form>
  );
}

function Field({
  label,
  name,
  type = "text",
  placeholder,
  required
}: {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <label className="grid gap-2 text-sm font-bold text-bone/70">
      {label}
      <input
        className="rounded-md border border-bone/10 bg-night px-3 py-3 text-sm text-bone"
        name={name}
        placeholder={placeholder}
        required={required}
        type={type}
      />
    </label>
  );
}

function Checkbox({ name, label }: { name: string; label: string }) {
  return (
    <label className="flex items-center gap-2 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm font-bold text-bone/70">
      <input className="h-4 w-4 accent-acid" name={name} type="checkbox" />
      {label}
    </label>
  );
}
