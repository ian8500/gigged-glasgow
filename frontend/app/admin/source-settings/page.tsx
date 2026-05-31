import { AdminPageHeader } from "@/components/admin/AdminSectionNav";

const sources = [
  ["Ticketmaster Discovery API", "Configured when TICKETMASTER_API_KEY is set", "API"],
  ["Manual CSV upload", "Enabled for local editorial imports", "Manual"],
  ["Bandsintown", "Placeholder until official credentials and terms review", "API"],
  ["Songkick", "Placeholder until official credentials and terms review", "API"],
  ["Public venue pages", "Robots.txt and terms-aware placeholder only", "Venue"]
];

export default function SourceSettingsPage() {
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Settings" title="Source settings" />
      <section className="grid gap-4">
        {sources.map(([name, status, kind]) => (
          <div key={name} className="flex flex-col justify-between gap-3 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 md:flex-row md:items-center">
            <div>
              <h2 className="font-display text-xl font-black text-bone">{name}</h2>
              <p className="mt-1 text-sm text-bone/55">{status}</p>
            </div>
            <span className="rounded bg-bone/10 px-3 py-1 text-xs font-black uppercase tracking-[0.14em] text-clyde">
              {kind}
            </span>
          </div>
        ))}
      </section>
    </main>
  );
}
