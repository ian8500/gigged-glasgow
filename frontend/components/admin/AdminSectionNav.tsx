const adminItems = [
  ["/admin", "Overview"],
  ["/admin/events-inbox", "Events inbox"],
  ["/admin/needs-review", "Needs review"],
  ["/admin/approved-events", "Approved"],
  ["/admin/venue-coverage", "Venue coverage"],
  ["/admin/weekly", "Weekly builder"],
  ["/admin/social", "Social posts"],
  ["/admin/instagram", "Instagram"],
  ["/admin/brand-settings", "Brand"],
  ["/admin/city-settings", "City"],
  ["/admin/source-settings", "Sources"]
];

export function AdminSectionNav() {
  return (
    <nav className="flex gap-2 overflow-x-auto rounded-lg border border-bone/10 bg-ink/45 p-2">
      {adminItems.map(([href, label]) => (
        <a
          key={href}
          href={href}
          className="whitespace-nowrap rounded-md px-3 py-2 text-sm font-bold text-bone/62 transition hover:bg-bone/10 hover:text-bone"
        >
          {label}
        </a>
      ))}
    </nav>
  );
}

export function AdminPageHeader({
  eyebrow,
  title,
  children
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="space-y-5">
      <AdminSectionNav />
      <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">{eyebrow}</p>
          <h1 className="mt-2 font-display text-5xl font-black leading-none text-bone">{title}</h1>
        </div>
        {children}
      </section>
    </div>
  );
}
