"use client";

import { useFormState } from "react-dom";

import {
  saveSettings,
  testAllSettings,
  testInstagram,
  testTicketmaster,
  type SettingsActionState
} from "@/app/settings/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { AppSettings } from "@/lib/types";

const sectionTitles: Record<string, string> = {
  event_data_apis: "Event data APIs",
  glasgow_search_configuration: "Glasgow search configuration",
  instagram_meta: "Instagram / Meta publishing preparation",
  brand_settings: "Brand settings"
};

const initialState: SettingsActionState = { ok: true, message: "" };

export function SettingsForm({ settings }: { settings: AppSettings }) {
  const [state, formAction] = useFormState(saveSettings, initialState);

  return (
    <div className="space-y-6">
      <form action={formAction} className="space-y-6">
        {Object.entries(settings.sections).map(([section, fields]) => (
          <section key={section} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
            <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
              <div>
                <p className="font-display text-sm uppercase tracking-[0.24em] text-acid">Settings</p>
                <h2 className="mt-2 font-display text-2xl font-black text-bone">
                  {sectionTitles[section] ?? section.replaceAll("_", " ")}
                </h2>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {fields.map((field) => (
                <label key={field.key} className="grid gap-2 text-sm font-bold text-bone/70">
                  <span className="flex items-center justify-between gap-3">
                    {field.label}
                    <span className="text-xs uppercase tracking-[0.12em] text-bone/35">
                      {field.source}
                    </span>
                  </span>
                  {booleanField(field.key) ? (
                    <select
                      name={field.key}
                      defaultValue={field.value || "false"}
                      className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
                    >
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  ) : longField(field.key) ? (
                    <textarea
                      name={field.key}
                      defaultValue={field.value}
                      placeholder={field.secret && !field.configured ? "Enter and save to configure" : undefined}
                      className="min-h-24 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
                    />
                  ) : (
                    <input
                      name={field.key}
                      type={field.secret ? "password" : "text"}
                      defaultValue={field.value}
                      placeholder={field.secret && !field.configured ? "Enter and save to configure" : undefined}
                      className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
                    />
                  )}
                  {field.secret ? (
                    <span className="text-xs font-medium text-bone/40">
                      Saved secrets are never returned in plain text.
                    </span>
                  ) : null}
                </label>
              ))}
            </div>
          </section>
        ))}

        <div className="flex flex-col gap-3 rounded-lg border border-bone/10 bg-ink/45 p-4 md:flex-row md:items-center md:justify-between">
          <p className={`text-sm font-semibold ${state.message ? (state.ok ? "text-clyde" : "text-poster") : "text-bone/45"}`}>
            {state.message || "Save changes or run a connection test."}
          </p>
          <SubmitButton
            pendingText="Saving"
            className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink"
          >
            Save settings
          </SubmitButton>
        </div>
      </form>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <h2 className="font-display text-2xl font-black text-bone">Connection tests</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <TestForm action={testTicketmaster} label="Test Ticketmaster" />
          <TestForm action={testInstagram} label="Test Instagram" />
          <TestForm action={testAllSettings} label="Test all" />
        </div>
      </section>
    </div>
  );
}

function TestForm({ action, label }: { action: () => Promise<SettingsActionState>; label: string }) {
  const [state, formAction] = useFormState(async () => action(), initialState);
  return (
    <form action={formAction} className="rounded-md border border-bone/10 bg-ink/45 p-4">
      <SubmitButton
        pendingText="Testing"
        className="w-full rounded-md border border-clyde px-3 py-2 text-sm font-black uppercase tracking-[0.14em] text-clyde"
      >
        {label}
      </SubmitButton>
      <p className={`mt-3 min-h-10 text-xs leading-5 ${state.message ? (state.ok ? "text-clyde" : "text-poster") : "text-bone/40"}`}>
        {state.message || "Not tested yet."}
      </p>
    </form>
  );
}

function booleanField(key: string) {
  return ["include_free_events", "include_paid_events", "manual_posting_mode"].includes(key);
}

function longField(key: string) {
  return [
    "skiddle_source_settings",
    "gigs_in_scotland_source_settings",
    "whats_on_glasgow_source_settings",
    "venue_whitelist",
    "venue_blacklist",
    "default_hashtags",
    "default_caption_footer",
    "colour_palette",
    "city_specific_hashtags"
  ].includes(key);
}
