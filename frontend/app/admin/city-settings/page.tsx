import { createCityBrand } from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { getCityBrands, getCityTemplates } from "@/lib/api";

export default async function CitySettingsPage() {
  const [brands, templates] = await Promise.all([getCityBrands(), getCityTemplates()]);
  const createdSlugs = new Set(brands.map((brand) => brand.slug));

  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Settings" title="City brand engine" />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {brands.map((brand) => (
          <div key={brand.slug} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-bold uppercase tracking-[0.18em] text-clyde">
                  {brand.city_name}
                </p>
                <h2 className="mt-2 font-display text-2xl font-black text-bone">
                  {brand.brand_name}
                </h2>
              </div>
              <span className="rounded bg-acid px-2 py-1 text-xs font-black uppercase text-ink">
                Live
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-bone/60">{brand.tagline}</p>
            <p className="mt-3 text-sm font-bold text-acid">{brand.handle}</p>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {Object.entries(brand.colours).slice(0, 3).map(([name, colour]) => (
                <div key={name} className="h-10 rounded border border-bone/10" style={{ backgroundColor: colour }} />
              ))}
            </div>
          </div>
        ))}
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">
              Create a city
            </p>
            <h2 className="mt-2 font-display text-3xl font-black text-bone">
              Reusable brand templates
            </h2>
          </div>
          <select className="rounded-md border border-bone/10 bg-night px-3 py-3 text-bone">
            {templates.map((template) => (
              <option key={template.slug}>{template.brand_name}</option>
            ))}
          </select>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-3">
          {templates
            .filter((template) => template.slug !== "glasgow")
            .map((template) => (
              <article key={template.slug} className="rounded-lg border border-bone/10 bg-ink/35 p-5">
                <p className="text-sm font-bold uppercase tracking-[0.18em] text-clyde">
                  {template.city_name}
                </p>
                <h3 className="mt-2 font-display text-2xl font-black text-bone">
                  {template.brand_name}
                </h3>
                <p className="mt-2 text-sm leading-6 text-bone/60">{template.tagline}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {template.hashtags.slice(0, 3).map((tag) => (
                    <span key={tag} className="rounded bg-bone/10 px-2 py-1 text-xs text-bone/65">
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="mt-4 text-sm text-bone/45">
                  {template.venues.length} starter venues · {template.radius_km} km radius
                </p>
                <form action={createCityBrand} className="mt-5">
                  <input type="hidden" name="templateSlug" value={template.slug} />
                  <button
                    disabled={createdSlugs.has(template.slug)}
                    className="w-full rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink disabled:cursor-not-allowed disabled:bg-bone/15 disabled:text-bone/35"
                  >
                    {createdSlugs.has(template.slug) ? "Created" : `Create ${template.brand_name}`}
                  </button>
                </form>
              </article>
            ))}
        </div>
      </section>

      <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
        <h2 className="font-display text-2xl font-black text-bone">Template fields</h2>
        <div className="mt-4 grid gap-3 text-sm text-bone/65 md:grid-cols-2">
          {[
            "city_name",
            "brand_name",
            "handle",
            "tagline",
            "colours",
            "venues",
            "coordinates",
            "radius",
            "hashtags",
            "local slang / voice notes",
            "default posting schedule",
          ].map((field) => (
            <div key={field} className="rounded bg-night px-3 py-2">
              {field}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
