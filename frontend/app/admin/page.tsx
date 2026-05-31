import { getDashboard, getSocialReviewQueue, getVenues } from "@/lib/api";
import { AdminDashboard } from "@/components/admin/AdminDashboard";

export default async function AdminPage() {
  const [dashboard, venues, reviewPosts] = await Promise.all([
    getDashboard(),
    getVenues(),
    getSocialReviewQueue()
  ]);

  return <AdminDashboard dashboard={dashboard} venues={venues} reviewPosts={reviewPosts} />;
}
