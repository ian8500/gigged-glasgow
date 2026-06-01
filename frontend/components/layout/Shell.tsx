import { LogoMark } from "@/components/brand/LogoMark";

const navItems = [
  { href: "/", label: "Radar" },
  { href: "/events", label: "Events" },
  { href: "/venues", label: "Venues" },
  { href: "/events/new", label: "Add Gig" },
  { href: "/weekly", label: "Weekly" },
  { href: "/social", label: "Social" },
  { href: "/scrape", label: "Sources" },
  { href: "/admin", label: "Admin" },
  { href: "/brand", label: "Brand" },
  { href: "/settings", label: "Settings" }
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-bone/10 bg-ink/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <LogoMark />
          <nav className="-mx-1 flex max-w-full gap-2 overflow-x-auto px-1 pb-1 md:flex-wrap md:justify-end md:overflow-visible md:pb-0">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="shrink-0 rounded-md px-3 py-2 text-sm font-semibold text-bone/70 transition hover:bg-bone/10 hover:text-bone"
              >
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-8">{children}</div>
    </div>
  );
}
