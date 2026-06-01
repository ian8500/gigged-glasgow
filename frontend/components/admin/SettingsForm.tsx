"use client";

import { useFormState } from "react-dom";

import { saveSettingsAction, type ActionState } from "@/app/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { AppSettings } from "@/lib/types";

const initialState: ActionState = { ok: false, message: "" };

export function SettingsForm({ settings }: { settings: AppSettings }) {
  const [state, formAction] = useFormState(saveSettingsAction, initialState);
  const value = settingValue(settings);

  return (
    <form action={formAction} className="space-y-6">
      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">Brand</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Field label="Brand name" name="brand_name" defaultValue={value("brand_name", "Gigged Glasgow")} />
          <Field label="Tagline" name="tagline" defaultValue={value("tagline", "Manual-first Glasgow gig guide")} />
          <Field label="Instagram handle" name="instagram_handle" defaultValue={value("instagram_handle", "@giggedglasgow")} />
          <Field
            label="Default hashtags"
            name="default_hashtags"
            defaultValue={value("default_hashtags", "#GiggedGlasgow #GlasgowGigs #GlasgowMusic")}
          />
        </div>
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">Manual posting</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Field label="Caption footer" name="default_caption_footer" defaultValue={value("default_caption_footer", "")} />
          <label className="grid gap-2 text-sm font-bold text-bone/70">
            Posting mode
            <select className="rounded-md border border-bone/10 bg-night px-3 py-3 text-sm text-bone" name="manual_posting_mode" defaultValue="true">
              <option value="true">Manual export and copy</option>
            </select>
          </label>
        </div>
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">Optional future APIs</p>
        <p className="mt-2 text-sm leading-6 text-bone/58">Optional future automation — not required.</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Field
            label="Ticketmaster API key optional"
            name="ticketmaster_api_key"
            type="password"
            defaultValue={value("ticketmaster_api_key", "")}
          />
          <Field
            label="Eventbrite API key optional"
            name="eventbrite_api_key"
            type="password"
            defaultValue={value("eventbrite_api_key", "")}
            help="Saved credential only — adapter not implemented yet"
          />
        </div>
      </section>

      <div className="flex flex-col gap-3 rounded-lg border border-bone/10 bg-night/80 p-4 md:flex-row md:items-center md:justify-between">
        <p className={`text-sm font-semibold ${state.message ? (state.ok ? "text-clyde" : "text-poster") : "text-bone/45"}`}>
          {state.message || "Saving requires the backend. If it is unavailable, this page will show a clear error."}
        </p>
        <SubmitButton pendingText="Saving" className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase text-ink">
          Save settings
        </SubmitButton>
      </div>
    </form>
  );
}

function Field({
  label,
  name,
  defaultValue,
  type = "text",
  help
}: {
  label: string;
  name: string;
  defaultValue: string;
  type?: string;
  help?: string;
}) {
  return (
    <label className="grid gap-2 text-sm font-bold text-bone/70">
      {label}
      <input
        className="rounded-md border border-bone/10 bg-night px-3 py-3 text-sm text-bone"
        defaultValue={defaultValue}
        name={name}
        type={type}
      />
      {help ? <span className="text-xs font-medium text-bone/42">{help}</span> : null}
    </label>
  );
}

function settingValue(settings: AppSettings) {
  const flattened = Object.values(settings.sections ?? {})
    .flat()
    .reduce<Record<string, string>>((acc, field) => {
      acc[field.key] = field.value ?? "";
      return acc;
    }, {});

  return (key: string, fallback: string) => settings.values?.[key] ?? flattened[key] ?? fallback;
}
