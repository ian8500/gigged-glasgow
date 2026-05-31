export function LogoMark() {
  return (
    <a href="/" className="flex items-center gap-3" aria-label="Gigged Glasgow home">
      <LogoGlyph className="h-11 w-11 shrink-0" />
      <div>
        <div className="font-display text-lg font-black leading-5 text-bone">Gigged Glasgow</div>
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-acid">
          Gig radar
        </div>
      </div>
    </a>
  );
}

export function LogoGlyph({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect width="64" height="64" rx="10" fill="#D6F84C" />
      <path d="M11 13H44V22H22V42H37V36H29V28H53V51H44V58H11V13Z" fill="#0E0E10" />
      <path d="M22 51H53V58H22V51Z" fill="#EF4D2F" />
      <path d="M46 10L54 10L54 18L46 18L46 10Z" fill="#28B8A7" />
    </svg>
  );
}

export function LogoLockup() {
  return (
    <div className="inline-flex items-center gap-4 rounded-lg border border-ink bg-paper p-4 text-ink shadow-print">
      <LogoGlyph className="h-16 w-16" />
      <div>
        <p className="font-display text-3xl font-black uppercase leading-none">Gigged</p>
        <p className="font-display text-3xl font-black uppercase leading-none text-poster">Glasgow</p>
        <p className="mt-2 text-xs font-black uppercase tracking-[0.22em]">Weekly gig radar</p>
      </div>
    </div>
  );
}
