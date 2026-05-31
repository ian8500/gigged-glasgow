import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SocialReviewQueue } from "@/components/admin/SocialReviewQueue";
import { SocialPostPreview } from "@/components/social/SocialPostPreview";
import { getSocialReviewQueue } from "@/lib/api";

export default async function SocialGeneratorPage() {
  const [reviewPosts, approvedPosts] = await Promise.all([
    getSocialReviewQueue("review"),
    getSocialReviewQueue("approved")
  ]);
  const posts = [...reviewPosts, ...approvedPosts];
  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Publishing desk" title="Social post generator" />
      <section className="grid gap-5 lg:grid-cols-3">
        <SocialPostPreview templateKey="weekly-roundup" compact />
        <SocialPostPreview templateKey="tonight" compact />
        <SocialPostPreview templateKey="under-15" compact />
      </section>
      <SocialReviewQueue posts={posts} />
    </main>
  );
}
