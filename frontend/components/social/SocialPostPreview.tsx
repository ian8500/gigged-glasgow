import clsx from "clsx";

import { socialTemplates, type SocialTemplateKey } from "@/lib/brand";

type SocialPostPreviewProps = {
  templateKey?: SocialTemplateKey;
  compact?: boolean;
};

const accentClasses: Record<string, string> = {
  acid: "bg-acid text-ink",
  clyde: "bg-clyde text-ink",
  poster: "bg-poster text-bone",
  amber: "bg-amber text-ink",
  tenement: "bg-tenement text-ink",
  plum: "bg-plum text-bone"
};

const borderClasses: Record<string, string> = {
  acid: "border-acid",
  clyde: "border-clyde",
  poster: "border-poster",
  amber: "border-amber",
  tenement: "border-tenement",
  plum: "border-plum"
};

const sampleEvents = [
  { day: "Fri", artist: "Cloth", venue: "Barrowland", price: "£22" },
  { day: "Sat", artist: "Bemz", venue: "SWG3", price: "£14" },
  { day: "Thu", artist: "Kathryn Joseph", venue: "Stereo", price: "£12" }
];

export function SocialPostPreview({
  templateKey = "weekly-roundup",
  compact = false
}: SocialPostPreviewProps) {
  const template = socialTemplates.find((item) => item.key === templateKey) ?? socialTemplates[0];
  const isCarousel = template.key === "carousel";

  if (isCarousel) {
    return <CarouselPreview compact={compact} />;
  }

  return (
    <article
      className={clsx(
        "poster-texture aspect-[4/5] overflow-hidden rounded-lg border bg-paper p-4 text-ink shadow-poster",
        borderClasses[template.accent],
        compact ? "min-h-[360px]" : "min-h-[440px]"
      )}
    >
      <div className="flex h-full flex-col justify-between border-[5px] border-ink bg-paper p-5">
        <header className="flex items-start justify-between gap-4">
          <div>
            <p
              className={clsx(
                "inline-flex rounded-sm px-2 py-1 text-[11px] font-black uppercase tracking-[0.16em]",
                accentClasses[template.accent]
              )}
            >
              {template.label}
            </p>
            <p className="mt-3 text-xs font-black uppercase tracking-[0.22em] text-ink/60">
              Gigged Glasgow
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-sm bg-ink font-display text-xl font-black text-acid">
            GG
          </div>
        </header>

        <section>
          <p className="font-editorial text-xl italic text-ink/65">{template.kicker}</p>
          <h2
            className={clsx(
              "mt-2 font-display font-black uppercase leading-[0.88]",
              compact ? "text-4xl" : "text-5xl"
            )}
          >
            {template.title}
          </h2>
        </section>

        <section className="space-y-2">
          {sampleEvents.map((event) => (
            <div key={`${template.key}-${event.day}`} className="grid grid-cols-[44px_1fr_auto] gap-3 border-t-[3px] border-ink pt-2">
              <span className="font-display text-lg font-black">{event.day}</span>
              <span>
                <span className="block text-sm font-black uppercase">{event.artist}</span>
                <span className="block text-xs font-bold text-ink/58">{event.venue}</span>
              </span>
              <span className="font-display text-sm font-black">{event.price}</span>
            </div>
          ))}
        </section>

        <footer className="flex items-center justify-between border-t-[5px] border-ink pt-3">
          <p className="text-xs font-black uppercase tracking-[0.16em]">@giggedglasgow</p>
          <p className="font-display text-sm font-black">SAVE / SHARE</p>
        </footer>
      </div>
    </article>
  );
}

function CarouselPreview({ compact }: { compact: boolean }) {
  const slides = [
    ["01", "This week, sorted", "Start here"],
    ["02", "Small rooms", "Hidden gems"],
    ["03", "Under £15", "Still loud"]
  ];

  return (
    <article
      className={clsx(
        "aspect-[4/5] rounded-lg border border-clyde bg-ink p-4 text-bone shadow-poster",
        compact ? "min-h-[360px]" : "min-h-[440px]"
      )}
    >
      <div className="grid h-full grid-cols-3 gap-2">
        {slides.map(([number, title, kicker]) => (
          <section key={number} className="flex flex-col justify-between rounded-sm bg-paper p-3 text-ink">
            <div>
              <p className="font-display text-2xl font-black text-poster">{number}</p>
              <h2 className="mt-4 font-display text-2xl font-black uppercase leading-none">
                {title}
              </h2>
            </div>
            <div>
              <p className="font-editorial text-lg italic text-ink/70">{kicker}</p>
              <p className="mt-3 text-[10px] font-black uppercase tracking-[0.12em]">
                Gigged Glasgow
              </p>
            </div>
          </section>
        ))}
      </div>
    </article>
  );
}
