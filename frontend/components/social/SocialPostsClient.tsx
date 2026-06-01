"use client";

import { useState, useTransition } from "react";

import { exportSocialPostAction, markSocialPostPostedAction } from "@/app/actions";
import type { SocialPost } from "@/lib/types";

const fallbackPosts: SocialPost[] = [
  {
    id: -1,
    city_id: 1,
    weekly_issue_id: null,
    event_id: null,
    platform: "instagram",
    template_name: "manual-example",
    caption: "This week in Glasgow: pick a venue, add the gig, approve it, then build your weekly caption here.",
    image_prompt: null,
    preview_payload: {
      title: "Manual weekly example",
      hashtags: ["#GiggedGlasgow", "#GlasgowGigs", "#GlasgowMusic"],
      alt_text: "Text-only weekly Glasgow gig guide preview."
    },
    status: "example",
    created_at: new Date().toISOString()
  }
];

export function SocialPostsClient({ posts }: { posts: SocialPost[] }) {
  const [localPosted, setLocalPosted] = useState<Record<number, string>>({});
  const [message, setMessage] = useState("");
  const [isPending, startTransition] = useTransition();
  const visiblePosts = posts.length ? posts : fallbackPosts;

  function markPosted(postId: number) {
    if (postId < 0) {
      setLocalPosted((current) => ({ ...current, [postId]: "posted manually" }));
      setMessage("Example marked posted locally.");
      return;
    }

    const formData = new FormData();
    formData.set("postId", String(postId));
    startTransition(async () => {
      const result = await markSocialPostPostedAction(formData);
      setLocalPosted((current) => ({ ...current, [postId]: result.ok ? "posted manually" : "local posted note" }));
      setMessage(result.ok ? "Marked as posted manually." : result.message);
    });
  }

  function exportPost(postId: number) {
    if (postId < 0) {
      setMessage("Example post has no backend export. Copy text manually.");
      return;
    }
    const formData = new FormData();
    formData.set("postId", String(postId));
    startTransition(async () => {
      const result = await exportSocialPostAction(formData);
      setMessage(result.message);
    });
  }

  return (
    <main className="space-y-6">
      <header>
        <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Social Post Export</p>
        <h1 className="mt-2 font-display text-4xl font-black leading-none text-bone md:text-5xl">Manual Instagram copy</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-bone/58">
          Copy captions, hashtags, and alt text. No Instagram automation is included.
        </p>
      </header>

      {message ? <p className="rounded-md border border-clyde/25 bg-clyde/10 px-4 py-3 text-sm text-clyde">{message}</p> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        {visiblePosts.map((post) => {
          const title = String(post.preview_payload?.title ?? post.template_name ?? "Social post");
          const caption = post.caption || String(post.preview_payload?.caption ?? "");
          const hashtags = Array.isArray(post.preview_payload?.hashtags)
            ? post.preview_payload?.hashtags.join(" ")
            : "#GiggedGlasgow #GlasgowGigs #GlasgowMusic";
          const altText = String(post.preview_payload?.alt_text ?? post.image_prompt ?? "Gigged Glasgow post graphic.");
          const status = localPosted[post.id] ?? post.status;

          return (
            <article key={post.id} className="rounded-lg border border-bone/10 bg-bone/[0.04] p-5">
              <div className="flex flex-col justify-between gap-3 md:flex-row">
                <div>
                  <h2 className="font-display text-2xl font-black text-bone">{title}</h2>
                  <p className="mt-1 text-sm uppercase tracking-[0.16em] text-bone/40">{post.platform}</p>
                </div>
                <span className="h-fit rounded bg-bone/10 px-3 py-1 text-xs font-black uppercase text-bone/62">{status}</span>
              </div>

              <TextBlock label="Caption" value={caption || "No caption generated yet."} />
              <TextBlock label="Hashtags" value={hashtags} />
              <TextBlock label="Alt text" value={altText} />

              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                <CopyButton label="Copy caption" value={caption} />
                <CopyButton label="Copy hashtags" value={hashtags} />
                <CopyButton label="Copy alt text" value={altText} />
                <button
                  className="rounded-md border border-clyde px-3 py-2 text-xs font-black uppercase text-clyde"
                  disabled={isPending}
                  onClick={() => markPosted(post.id)}
                  type="button"
                >
                  Mark as posted manually
                </button>
                {post.id > 0 ? (
                  <button
                    className="rounded-md border border-bone/20 px-3 py-2 text-xs font-black uppercase text-bone/65"
                    disabled={isPending}
                    onClick={() => exportPost(post.id)}
                    type="button"
                  >
                    Export files
                  </button>
                ) : null}
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}

function TextBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="mt-5">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-bone/35">{label}</p>
      <p className="mt-2 whitespace-pre-wrap rounded-md border border-bone/10 bg-night p-3 text-sm leading-6 text-bone/72">
        {value}
      </p>
    </div>
  );
}

function CopyButton({ label, value }: { label: string; value: string }) {
  return (
    <button
      className="rounded-md bg-acid px-3 py-2 text-xs font-black uppercase text-ink disabled:cursor-not-allowed disabled:opacity-50"
      disabled={!value}
      onClick={() => navigator.clipboard.writeText(value)}
      type="button"
    >
      {label}
    </button>
  );
}
