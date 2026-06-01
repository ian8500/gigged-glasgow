"use server";

import { revalidatePath } from "next/cache";

import {
  approveEvent,
  approveScrapeCandidate,
  convertScrapeCandidate,
  createEvent,
  exportSocialPost,
  markEventTopPick,
  markSocialPostPosted,
  markVenueChecked,
  markVenueManualOnly,
  rejectEvent,
  rejectScrapeCandidate,
  runCityScrape,
  saveSettings,
  scrapeVenue,
  updateEvent,
  updateVenueScraperConfig
} from "@/lib/api";

export type ActionState = {
  ok: boolean;
  message: string;
  intent?: string;
  id?: number;
};

const initialError = "Something went wrong. Try again after checking the backend is running.";

export async function createGigAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const title = text(formData, "title");
  const venueSlug = text(formData, "venue_slug");
  const date = text(formData, "date");
  const time = text(formData, "time") || "19:30";
  const intent = text(formData, "intent") || "save";

  if (!title || !venueSlug || !date) {
    return { ok: false, message: "Title, venue, and date are required.", intent };
  }

  const result = await createEvent({
    title,
    artist: text(formData, "artist"),
    venue_slug: venueSlug,
    starts_at: `${date}T${time}:00`,
    ticket_url: text(formData, "ticket_url") || null,
    image_url: text(formData, "image_url") || null,
    price: text(formData, "price") || null,
    genre: text(formData, "genre") || null,
    notes: text(formData, "notes") || null,
    top_pick: formData.get("top_pick") === "on",
    hidden_gem: formData.get("hidden_gem") === "on",
    cheap_gig: formData.get("cheap_gig") === "on"
  });

  if (result.ok) {
    revalidatePath("/");
    revalidatePath("/events");
    revalidatePath("/weekly");
  }

  return { ok: result.ok, message: result.message || initialError, intent, id: result.data?.id };
}

export async function approveEventAction(formData: FormData) {
  await approveEvent(Number(formData.get("eventId")));
  revalidateEvents();
}

export async function rejectEventAction(formData: FormData) {
  await rejectEvent(Number(formData.get("eventId")));
  revalidateEvents();
}

export async function markTopPickAction(formData: FormData) {
  await markEventTopPick(Number(formData.get("eventId")));
  revalidateEvents();
}

export async function updateEventAction(formData: FormData) {
  await updateEvent(Number(formData.get("eventId")), {
    title: text(formData, "title") || undefined,
    starts_at: text(formData, "starts_at") || undefined,
    ticket_url: text(formData, "ticket_url") || null,
    genre: text(formData, "genre") || null,
    notes: text(formData, "notes") || null,
    price: text(formData, "price") || null
  });
  revalidateEvents();
}

export async function markVenueCheckedAction(formData: FormData) {
  const result = await markVenueChecked(Number(formData.get("venueId")));
  revalidatePath("/venues");
  return result;
}

export async function runCityScrapeAction() {
  const result = await runCityScrape();
  revalidatePath("/scrape");
  revalidatePath("/venues");
  return result;
}

export async function scrapeVenueAction(formData: FormData) {
  const result = await scrapeVenue(Number(formData.get("venueId")));
  revalidatePath("/scrape");
  revalidatePath("/venues");
  return result;
}

export async function markVenueManualOnlyAction(formData: FormData) {
  const result = await markVenueManualOnly(Number(formData.get("venueId")));
  revalidatePath("/venues");
  return result;
}

export async function updateVenueScraperConfigAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const venueId = Number(formData.get("venueId"));
  const rawConfig = text(formData, "scraper_selector_config");
  let parsedConfig: Record<string, unknown> | null = null;
  if (rawConfig) {
    try {
      parsedConfig = JSON.parse(rawConfig) as Record<string, unknown>;
    } catch {
      return { ok: false, message: "Selector config must be valid JSON." };
    }
  }
  const result = await updateVenueScraperConfig(venueId, {
    source_mode: text(formData, "source_mode") || "manual_only",
    scraper_selector_config: parsedConfig
  });
  revalidatePath("/venues");
  return { ok: result.ok, message: result.message || initialError };
}

export async function approveScrapeCandidateAction(formData: FormData) {
  await approveScrapeCandidate(Number(formData.get("candidateId")));
  revalidatePath("/scrape");
}

export async function rejectScrapeCandidateAction(formData: FormData) {
  await rejectScrapeCandidate(Number(formData.get("candidateId")));
  revalidatePath("/scrape");
}

export async function convertScrapeCandidateAction(formData: FormData) {
  await convertScrapeCandidate(Number(formData.get("candidateId")));
  revalidatePath("/scrape");
  revalidatePath("/events");
  revalidatePath("/weekly");
}

export async function saveSettingsAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const payload: Record<string, string> = {};
  for (const [key, value] of formData.entries()) {
    if (!key.startsWith("$")) {
      payload[key] = String(value);
    }
  }

  const result = await saveSettings(payload);
  if (result.ok) {
    revalidatePath("/settings");
  }
  return { ok: result.ok, message: result.message || initialError };
}

export async function exportSocialPostAction(formData: FormData) {
  const result = await exportSocialPost(Number(formData.get("postId")));
  revalidatePath("/social");
  return result;
}

export async function markSocialPostPostedAction(formData: FormData) {
  const result = await markSocialPostPosted(Number(formData.get("postId")));
  revalidatePath("/social");
  return result;
}

function text(formData: FormData, key: string) {
  return String(formData.get(key) ?? "").trim();
}

function revalidateEvents() {
  revalidatePath("/");
  revalidatePath("/events");
  revalidatePath("/weekly");
}
