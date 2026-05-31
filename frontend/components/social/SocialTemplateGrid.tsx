import { SocialPostPreview } from "@/components/social/SocialPostPreview";
import { socialTemplates } from "@/lib/brand";

export function SocialTemplateGrid() {
  return (
    <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">
            Instagram system
          </p>
          <h2 className="mt-2 font-display text-3xl font-black text-bone">
            Post and carousel templates
          </h2>
        </div>
        <p className="max-w-xl text-sm leading-6 text-bone/60">
          Every template uses the same grid, type scale and city-lockup logic, so the system can
          become Gigged Manchester or Gigged Edinburgh without redesigning the product.
        </p>
      </div>

      <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {socialTemplates.map((template) => (
          <div key={template.key} className="space-y-3">
            <SocialPostPreview templateKey={template.key} compact />
            <div>
              <h3 className="font-display text-xl font-black text-bone">{template.name}</h3>
              <p className="mt-1 text-sm text-bone/55">{template.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
