import { runSourceIngest, testSource, updateSource } from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SubmitButton } from "@/components/admin/SubmitButton";
import { getSources } from "@/lib/api";

export default async function SourceSettingsPage() {
  const sources = await getSources();

  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Settings" title="Source settings" />
      <section className="grid gap-4">
        {sources.length === 0 ? (
          <div className="rounded-lg border border-dashed border-bone/20 bg-bone/[0.04] p-8 text-bone/55">
            No sources are registered yet. Seed Glasgow or run ingestion to create source records.
          </div>
        ) : (
          sources.map((source) => {
            const health = source.health ?? {
              status: "untested",
              last_tested_at: null,
              last_success_at: null,
              last_ingest_at: null,
              last_error: null,
              configured: false,
              enabled: source.is_enabled,
              events_last_found: 0,
              warnings: []
            };
            return (
            <div
              key={source.id}
              className="grid gap-4 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 lg:grid-cols-[1fr_260px]"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-display text-xl font-black text-bone">{source.name}</h2>
                  <span className="rounded bg-bone/10 px-3 py-1 text-xs font-black uppercase tracking-[0.14em] text-clyde">
                    {source.kind}
                  </span>
                  <span className={`rounded px-3 py-1 text-xs font-black uppercase tracking-[0.14em] ${source.is_enabled ? "bg-clyde text-ink" : "bg-bone/10 text-bone/45"}`}>
                    {source.is_enabled ? "Enabled" : "Disabled"}
                  </span>
                  <span className={`rounded px-3 py-1 text-xs font-black uppercase tracking-[0.14em] ${health.status === "working" ? "bg-acid text-ink" : health.status === "failing" ? "bg-poster text-ink" : "bg-bone/10 text-bone/55"}`}>
                    {health.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-bone/62">{source.limitations ?? source.notes}</p>
                <div className="mt-4 grid gap-2 text-xs text-bone/45 md:grid-cols-2">
                  <p>Configured: {health.configured ? "yes" : "no"}</p>
                  <p>Last checked: {health.last_tested_at ?? "untested"}</p>
                  <p>Last ingest: {health.last_ingest_at ?? "never"}</p>
                  <p>Last found: {health.events_last_found}</p>
                  <p>API: {source.official_api_available ?? "unknown"}</p>
                  <p>Automation: {source.automation_allowed ?? "unknown"}</p>
                </div>
                {health.last_error ? (
                  <p className="mt-3 text-xs leading-5 text-poster">{health.last_error}</p>
                ) : null}
                <a className="mt-3 inline-block text-xs font-black uppercase tracking-[0.14em] text-clyde" href={`/admin/venue-coverage?source=${encodeURIComponent(source.name)}`}>
                  View logs
                </a>
              </div>
              <div className="space-y-3">
                <form action={updateSource} className="space-y-3">
                  <input type="hidden" name="sourceId" value={source.id} />
                  <textarea
                    name="notes"
                    defaultValue={source.notes ?? ""}
                    placeholder="Source notes"
                    className="min-h-20 w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
                  />
                  <select
                    name="is_enabled"
                    defaultValue={String(source.is_enabled)}
                    className="w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
                  >
                    <option value="true">Enabled</option>
                    <option value="false">Disabled</option>
                  </select>
                  <SubmitButton pendingText="Saving" className="w-full rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
                    Save source
                  </SubmitButton>
                </form>
                <form action={testSource}>
                  <input type="hidden" name="sourceId" value={source.id} />
                  <SubmitButton pendingText="Testing" className="w-full rounded-md border border-clyde px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-clyde">
                    Test source
                  </SubmitButton>
                </form>
                <form action={runSourceIngest}>
                  <input type="hidden" name="sourceId" value={source.id} />
                  <SubmitButton pendingText="Running" className="w-full rounded-md border border-bone/20 px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-bone">
                    Run source ingest
                  </SubmitButton>
                </form>
              </div>
            </div>
          );
        })
        )}
      </section>
    </main>
  );
}
