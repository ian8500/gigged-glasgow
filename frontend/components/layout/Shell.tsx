import { LogoMark } from "@/components/brand/LogoMark";

const navItems = [
  { href: "/", label: "Radar" },
  { href: "/admin", label: "Admin" },
  { href: "/brand", label: "Brand" },
  { href: "/events", label: "Events" },
  { href: "/venues", label: "Venues" }
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-bone/10 bg-ink/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <LogoMark />
          <nav className="flex items-center gap-2">
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
