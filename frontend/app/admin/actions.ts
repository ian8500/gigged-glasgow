"use server";

import { revalidatePath } from "next/cache";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "change-me-in-production";

async function adminFetch(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": ADMIN_API_KEY,
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    throw new Error(`Admin request failed: ${response.status}`);
  }
}

export async function generateSocialPosts() {
  await adminFetch("/admin/social/generate?city=glasgow", { method: "POST" });
  revalidatePath("/admin");
}

export async function approveSocialPost(formData: FormData) {
  const postId = formData.get("postId");
  await adminFetch(`/social/posts/${postId}/approve`, { method: "POST" });
  revalidatePath("/admin");
}

export async function rejectSocialPost(formData: FormData) {
  const postId = formData.get("postId");
  await adminFetch(`/social/posts/${postId}/reject`, { method: "POST" });
  revalidatePath("/admin");
}

export async function scheduleSocialPost(formData: FormData) {
  const postId = formData.get("postId");
  await adminFetch(`/admin/social/${postId}/schedule`, { method: "POST" });
  revalidatePath("/admin");
  revalidatePath("/admin/social");
  revalidatePath("/admin/instagram");
}

export async function regenerateSocialPost(formData: FormData) {
  const postId = formData.get("postId");
  await adminFetch(`/social/posts/${postId}/regenerate`, { method: "POST" });
  revalidatePath("/admin");
}

export async function editSocialPost(formData: FormData) {
  const postId = formData.get("postId");
  await adminFetch(`/social/posts/${postId}`, {
    method: "PATCH",
    body: JSON.stringify({
      caption: formData.get("caption"),
      title: formData.get("title"),
      description: formData.get("description")
    })
  });
  revalidatePath("/admin");
}

export async function approveEvent(formData: FormData) {
  await adminFetch(`/events/${formData.get("eventId")}/approve`, { method: "POST" });
  revalidateAdmin();
}

export async function rejectEvent(formData: FormData) {
  await adminFetch(`/events/${formData.get("eventId")}/reject`, { method: "POST" });
  revalidateAdmin();
}

export async function markTopPick(formData: FormData) {
  await adminFetch(`/events/${formData.get("eventId")}/mark-top-pick?enabled=true`, {
    method: "POST"
  });
  revalidateAdmin();
}

export async function markSponsored(formData: FormData) {
  await adminFetch(`/admin/events/${formData.get("eventId")}/sponsored?enabled=true`, {
    method: "POST"
  });
  revalidateAdmin();
}

export async function editEvent(formData: FormData) {
  await adminFetch(`/events/${formData.get("eventId")}`, {
    method: "PATCH",
    body: JSON.stringify({
      title: formData.get("title"),
      starts_at: formData.get("starts_at"),
      ticket_url: formData.get("ticket_url"),
      genre: formData.get("genre"),
      editorial_note: formData.get("editorial_note")
    })
  });
  revalidateAdmin();
}

export async function mergeDuplicateEvents(formData: FormData) {
  await adminFetch(`/admin/events/${formData.get("keeperId")}/merge/${formData.get("duplicateId")}`, {
    method: "POST"
  });
  revalidateAdmin();
}

export async function addManualEvent(formData: FormData) {
  const title = String(formData.get("title") ?? "");
  if (!title.trim()) {
    throw new Error("Event title is required");
  }
  await adminFetch("/events", {
    method: "POST",
    body: JSON.stringify({
      city_slug: "glasgow",
      venue_slug: formData.get("venue_slug"),
      title,
      slug: title.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
      starts_at: formData.get("starts_at"),
      ticket_url: formData.get("ticket_url"),
      genre: formData.get("genre")
    })
  });
  revalidateAdmin();
}

export async function uploadCsv(formData: FormData) {
  const file = formData.get("csv");
  if (!(file instanceof File)) {
    throw new Error("CSV file is required");
  }
  await adminFetch("/admin/events/import-csv", {
    method: "POST",
    body: JSON.stringify({
      city_slug: "glasgow",
      csv_text: await file.text()
    })
  });
  revalidateAdmin();
}

export async function generateWeeklyRoundup() {
  await adminFetch("/weekly/run?city=glasgow", { method: "POST" });
  revalidateAdmin();
}

export async function seedVenueCoverage() {
  await adminFetch("/admin/venue-coverage/seed/glasgow", { method: "POST" });
  revalidatePath("/admin/venue-coverage");
  revalidatePath("/admin");
}

export async function checkAllVenues() {
  await adminFetch("/venues/bulk-check?city=glasgow", { method: "POST" });
  revalidatePath("/admin/venue-coverage");
  revalidatePath("/admin/weekly");
}

export async function checkVenueNow(formData: FormData) {
  await adminFetch(`/venues/${formData.get("venueId")}/check`, { method: "POST" });
  revalidatePath("/admin/venue-coverage");
}

export async function markVenueManualOnly(formData: FormData) {
  await adminFetch(`/venues/${formData.get("venueId")}/mark-manual-only`, { method: "POST" });
  revalidatePath("/admin/venue-coverage");
}

export async function markVenueSourceBroken(formData: FormData) {
  await adminFetch(`/venues/${formData.get("venueId")}/mark-source-broken`, { method: "POST" });
  revalidatePath("/admin/venue-coverage");
}

export async function createVenue(formData: FormData) {
  const name = String(formData.get("name") ?? "");
  if (!name.trim()) {
    throw new Error("Venue name is required");
  }
  await adminFetch("/venues", {
    method: "POST",
    body: JSON.stringify({
      city_slug: "glasgow",
      name,
      slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, ""),
      address: formData.get("address") || null,
      postcode: formData.get("postcode") || null,
      website_url: formData.get("website_url") || null,
      event_listings_url: formData.get("event_listings_url") || null,
      ticketing_url: formData.get("ticketing_url") || null,
      instagram_handle: formData.get("instagram_handle") || null,
      coverage_status: formData.get("coverage_status") || "manual_only",
      notes: formData.get("notes") || null,
      is_whitelisted: true
    })
  });
  revalidatePath("/admin/venue-coverage");
  revalidatePath("/venues");
}

export async function editVenue(formData: FormData) {
  await adminFetch(`/venues/${formData.get("venueId")}`, {
    method: "PATCH",
    body: JSON.stringify({
      name: formData.get("name"),
      address: formData.get("address") || null,
      postcode: formData.get("postcode") || null,
      website_url: formData.get("website_url") || null,
      event_listings_url: formData.get("event_listings_url") || null,
      ticketing_url: formData.get("ticketing_url") || null,
      instagram_handle: formData.get("instagram_handle") || null,
      coverage_status: formData.get("coverage_status"),
      notes: formData.get("notes") || null
    })
  });
  revalidatePath("/admin/venue-coverage");
  revalidatePath("/venues");
}

export async function mergeDuplicateVenues(formData: FormData) {
  await adminFetch(`/venues/${formData.get("keeperId")}/merge/${formData.get("duplicateId")}`, {
    method: "POST"
  });
  revalidatePath("/admin/venue-coverage");
}

export async function exportSocialPost(formData: FormData) {
  await adminFetch(`/social/posts/${formData.get("postId")}/export`, { method: "POST" });
  revalidatePath("/admin/social");
  revalidatePath("/admin/instagram");
}

export async function markSocialPostPosted(formData: FormData) {
  await adminFetch(`/social/posts/${formData.get("postId")}/mark-posted`, { method: "POST" });
  revalidatePath("/admin/social");
  revalidatePath("/admin/instagram");
}

export async function createCityBrand(formData: FormData) {
  await adminFetch(`/admin/city-brands/${formData.get("templateSlug")}`, { method: "POST" });
  revalidatePath("/admin/city-settings");
}

export async function updateSource(formData: FormData) {
  await adminFetch(`/sources/${formData.get("sourceId")}`, {
    method: "PATCH",
    body: JSON.stringify({
      is_enabled: formData.get("is_enabled") === "true",
      notes: formData.get("notes") || null
    })
  });
  revalidatePath("/admin/source-settings");
}

function revalidateAdmin() {
  [
    "/admin",
    "/admin/events-inbox",
    "/admin/needs-review",
    "/admin/approved-events",
    "/admin/weekly",
    "/admin/social",
    "/admin/venue-coverage"
  ].forEach((path) => revalidatePath(path));
}
