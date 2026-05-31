import { updateSource } from "@/app/admin/actions";
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
          sources.map((source) => (
            <form
              key={source.id}
              action={updateSource}
              className="grid gap-4 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 lg:grid-cols-[1fr_220px]"
            >
              <input type="hidden" name="sourceId" value={source.id} />
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-display text-xl font-black text-bone">{source.name}</h2>
                  <span className="rounded bg-bone/10 px-3 py-1 text-xs font-black uppercase tracking-[0.14em] text-clyde">
                    {source.kind}
                  </span>
                  <span className={`rounded px-3 py-1 text-xs font-black uppercase tracking-[0.14em] ${source.is_enabled ? "bg-clyde text-ink" : "bg-bone/10 text-bone/45"}`}>
                    {source.is_enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <textarea
                  name="notes"
                  defaultValue={source.notes ?? ""}
                  placeholder="Source notes"
                  className="mt-3 min-h-20 w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
                />
              </div>
              <div className="space-y-3">
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
              </div>
            </form>
          ))
        )}
      </section>
    </main>
  );
}
