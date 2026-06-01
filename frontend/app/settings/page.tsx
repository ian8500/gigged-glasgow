import { SettingsForm } from "@/components/admin/SettingsForm";
import { getSettings } from "@/lib/api";

export default async function SettingsPage() {
  const settings = await getSettings();

  return (
    <main className="space-y-8">
      <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Configuration</p>
          <h1 className="mt-2 font-display text-5xl font-black leading-none text-bone">Settings</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/60">
            Keep brand defaults and manual posting details simple. API keys are optional future automation and are not required.
          </p>
        </div>
      </section>
      <SettingsForm settings={settings} />
    </main>
  );
}
