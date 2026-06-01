import { SocialPostsClient } from "@/components/social/SocialPostsClient";
import { getSocialPosts } from "@/lib/api";

export default async function SocialPage() {
  const posts = await getSocialPosts();
  return <SocialPostsClient posts={posts} />;
}
