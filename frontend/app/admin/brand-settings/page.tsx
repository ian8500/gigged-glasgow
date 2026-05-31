import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { BrandSystem } from "@/components/brand/BrandSystem";

export default function BrandSettingsPage() {
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Settings" title="Brand settings" />
      <BrandSystem />
    </main>
  );
}
