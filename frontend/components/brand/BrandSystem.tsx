import { LogoLockup } from "@/components/brand/LogoMark";
import { SocialTemplateGrid } from "@/components/social/SocialTemplateGrid";
import { brand } from "@/lib/brand";

const palette = [
  ["Ink", brand.colors.ink, "Primary text and poster outline"],
  ["Night", brand.colors.night, "Dashboard surface"],
  ["Asphalt", brand.colors.asphalt, "Secondary surface"],
  ["Acid", brand.colors.acid, "Radar signal"],
  ["Clyde", brand.colors.clyde, "Information and trust"],
  ["Poster", brand.colors.poster, "Urgent editorial accent"],
  ["Plum", brand.colors.plum, "Premium spotlight"],
  ["Tenement", brand.colors.tenement, "Local warmth"],
  ["Amber", brand.colors.amber, "Price-led callouts"],
  ["Paper", brand.colors.paper, "Instagram poster stock"]
];

export function BrandSystem() {
  return (
    <main className="space-y-8">
      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">
            Brand system
          </p>
          <h1 className="mt-3 font-display text-5xl font-black leading-none text-bone">
            Modern gig poster. Useful city guide.
          </h1>
          <p className="mt-5 max-w-2xl text-bone/65">
            A Glasgow-first identity built from heavy poster type, sharp information hierarchy,
            civic colour accents, and layouts that scale to any city.
          </p>
        </div>
        <div className="flex items-center justify-center rounded-lg bg-paper p-8">
          <LogoLockup />
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Colour palette</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {palette.map(([name, value, usage]) => (
              <div key={name} className="rounded-md border border-bone/10 bg-ink/35 p-3">
                <div
                  className="h-16 rounded border border-bone/10"
                  style={{ backgroundColor: value }}
                />
                <div className="mt-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="font-display text-lg font-black text-bone">{name}</p>
                    <p className="text-sm text-bone/55">{usage}</p>
                  </div>
                  <code className="text-xs text-acid">{value}</code>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
          <h2 className="font-display text-2xl font-black text-bone">Typography</h2>
          <div className="mt-5 space-y-5">
            <div className="border-b border-bone/10 pb-5">
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-clyde">Display</p>
              <p className="mt-2 font-display text-5xl font-black leading-none text-bone">
                GIGS WORTH KNOWING
              </p>
              <p className="mt-2 text-sm text-bone/55">{brand.typography.display}</p>
            </div>
            <div className="border-b border-bone/10 pb-5">
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-clyde">UI sans</p>
              <p className="mt-2 text-xl font-bold text-bone">
                Clear venue, date, price and review information for editors.
              </p>
              <p className="mt-2 text-sm text-bone/55">{brand.typography.sans}</p>
            </div>
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-clyde">Editorial</p>
              <p className="mt-2 font-editorial text-3xl italic text-bone">
                Local recommendations with taste, not hype.
              </p>
              <p className="mt-2 text-sm text-bone/55">{brand.typography.editorial}</p>
            </div>
          </div>
        </div>
      </section>

      <SocialTemplateGrid />
    </main>
  );
}
