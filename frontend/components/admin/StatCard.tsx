import clsx from "clsx";

type Tone = "acid" | "clyde" | "poster" | "plum";

const tones: Record<Tone, string> = {
  acid: "border-acid/35 text-acid",
  clyde: "border-clyde/35 text-clyde",
  poster: "border-poster/35 text-poster",
  plum: "border-plum/60 text-bone"
};

export function StatCard({ label, value, tone }: { label: string; value: number; tone: Tone }) {
  return (
    <div className={clsx("rounded-lg border bg-bone/[0.04] p-5", tones[tone])}>
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-bone/50">{label}</p>
      <p className="mt-3 font-display text-4xl font-black">{value}</p>
    </div>
  );
}

