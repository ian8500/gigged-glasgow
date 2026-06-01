import { LogoMark } from "@/components/brand/LogoMark";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/venues", label: "Venues" },
  { href: "/scrape", label: "Auto Finder" },
  { href: "/events/new", label: "Add Gig" },
  { href: "/events", label: "Events" },
  { href: "/weekly", label: "Weekly" },
  { href: "/social", label: "Social Posts" },
  { href: "/settings", label: "Settings" }
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-bone/10 bg-ink/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <LogoMark />
          <nav className="flex flex-wrap items-center justify-end gap-2">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="rounded-md px-3 py-2 text-sm font-semibold text-bone/70 transition hover:bg-bone/10 hover:text-bone"
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
