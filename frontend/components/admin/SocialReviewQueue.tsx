"use client";

import { useState } from "react";

import {
  approveSocialPost,
  editSocialPost,
  exportSocialPost,
  generateSocialPosts,
  markSocialPostPosted,
  regenerateSocialPost,
  rejectSocialPost,
  scheduleSocialPost
} from "@/app/admin/actions";
import { SubmitButton } from "@/components/admin/SubmitButton";
import type { SocialPost } from "@/lib/types";

export function SocialReviewQueue({ posts }: { posts: SocialPost[] }) {
  return (
    <section className="rounded-lg border border-bone/10 bg-bone/[0.04] p-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">
            Review queue
          </p>
          <h2 className="mt-2 font-display text-3xl font-black text-bone">
            Instagram drafts awaiting approval
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-bone/60">
            Generate, edit, approve, reject, or regenerate posts. Approved posts are still not
            automatically published.
          </p>
        </div>
        <form action={generateSocialPosts}>
          <SubmitButton pendingText="Generating" className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink">
            Generate drafts
          </SubmitButton>
        </form>
      </div>

      <div className="mt-6 space-y-4">
        {posts.length === 0 ? (
          <div className="rounded-md border border-dashed border-bone/20 p-8 text-bone/55">
            No posts in review. Generate drafts after approving events.
          </div>
        ) : (
          posts.map((post) => <ReviewCard key={post.id} post={post} />)
        )}
      </div>
    </section>
  );
}

function ReviewCard({ post }: { post: SocialPost }) {
  const payload = post.preview_payload ?? {};
  const events = payload.events ?? [];

  return (
    <article className="grid gap-4 rounded-lg border border-bone/10 bg-ink/35 p-5 lg:grid-cols-[1fr_360px]">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded bg-clyde px-2 py-1 text-xs font-black uppercase tracking-[0.14em] text-ink">
            {post.template_name.replace(/_/g, " ")}
          </span>
          <span className="text-xs font-bold uppercase tracking-[0.14em] text-bone/45">
            {post.status}
          </span>
        </div>
        <h3 className="mt-3 font-display text-2xl font-black text-bone">
          {String(payload.title ?? "Untitled social draft")}
        </h3>
        <p className="mt-2 text-sm leading-6 text-bone/62">
          {String(payload.description ?? post.image_prompt ?? "")}
        </p>

        <div className="mt-4 grid gap-2">
          {events.map((event) => (
            <div
              key={`${event.event_title}-${event.date}`}
              className="rounded-md border border-bone/10 bg-bone/[0.04] p-3 text-sm"
            >
              <div className="font-black text-bone">{event.artist}</div>
              <div className="mt-1 text-bone/55">
                {event.venue} · {event.date} · Doors {event.door_time ?? "TBC"} ·{" "}
                {event.ticket_price}
              </div>
              <div className="mt-2 text-xs text-bone/40">
                Internal source: {event.source_attribution}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 text-xs leading-5 text-bone/45">
          PNG: {payload.exports?.png_path ?? "Not exported"} <br />
          JSON: {payload.exports?.json_path ?? "Not exported"}
        </div>
      </div>

      <div className="space-y-3">
        <form action={editSocialPost} className="space-y-3">
          <input type="hidden" name="postId" value={post.id} />
          <input
            name="title"
            defaultValue={String(payload.title ?? "")}
            className="w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
            aria-label="Post title"
          />
          <textarea
            name="description"
            defaultValue={String(payload.description ?? "")}
            className="h-20 w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
            aria-label="Post description"
          />
          <textarea
            name="caption"
            defaultValue={post.caption ?? ""}
            className="h-36 w-full rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone"
            aria-label="Post caption"
          />
          <SubmitButton pendingText="Saving" className="w-full rounded-md border border-clyde px-3 py-2 text-sm font-black uppercase tracking-[0.14em] text-clyde">
            Save edits
          </SubmitButton>
        </form>
        <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
          <form action={approveSocialPost}>
            <input type="hidden" name="postId" value={post.id} />
            <SubmitButton pendingText="Approving" className="w-full rounded-md bg-acid px-3 py-2 text-xs font-black uppercase text-ink">
              Approve
            </SubmitButton>
          </form>
          {post.status === "approved" ? (
            <form action={scheduleSocialPost}>
              <input type="hidden" name="postId" value={post.id} />
              <SubmitButton pendingText="Scheduling" className="w-full rounded-md bg-clyde px-3 py-2 text-xs font-black uppercase text-ink">
                Schedule
              </SubmitButton>
            </form>
          ) : (
            <div className="rounded-md bg-bone/10 px-3 py-2 text-center text-xs font-black uppercase text-bone/35" title="Approve the post before scheduling.">
              Schedule
            </div>
          )}
          <form action={regenerateSocialPost}>
            <input type="hidden" name="postId" value={post.id} />
            <SubmitButton pendingText="Regenerating" className="w-full rounded-md bg-plum px-3 py-2 text-xs font-black uppercase text-bone">
              Regen
            </SubmitButton>
          </form>
          <form action={rejectSocialPost}>
            <input type="hidden" name="postId" value={post.id} />
            <SubmitButton pendingText="Rejecting" className="w-full rounded-md bg-poster px-3 py-2 text-xs font-black uppercase text-bone">
              Reject
            </SubmitButton>
          </form>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <form action={exportSocialPost}>
            <input type="hidden" name="postId" value={post.id} />
            <SubmitButton pendingText="Exporting" className="w-full rounded-md border border-acid px-3 py-2 text-xs font-black uppercase text-acid">
              Export
            </SubmitButton>
          </form>
          <form action={markSocialPostPosted}>
            <input type="hidden" name="postId" value={post.id} />
            <SubmitButton pendingText="Marking" className="w-full rounded-md border border-bone/20 px-3 py-2 text-xs font-black uppercase text-bone/70">
              Mark posted
            </SubmitButton>
          </form>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <CopyButton label="Copy caption" value={post.caption ?? ""} />
          <CopyButton label="Copy hashtags" value={(payload.hashtags ?? []).join(" ")} />
          <CopyButton label="Copy alt" value={String(payload.alt_text ?? "")} />
        </div>
        <div className="rounded-md border border-bone/10 bg-bone/[0.03] p-3 text-xs leading-5 text-bone/55">
          Manual fallback: use exported PNGs, caption, hashtags and alt text. Official Meta
          publishing is prepared but not active.
        </div>
      </div>
    </article>
  );
}

function CopyButton({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      disabled={!value}
      onClick={async () => {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1800);
      }}
      className="rounded-md border border-bone/15 px-2 py-2 text-xs font-black uppercase text-bone/65 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {copied ? "Copied" : label}
    </button>
  );
}
