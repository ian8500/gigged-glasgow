import type {
  AdminEvent,
  AppSettings,
  CityBrand,
  CityTemplate,
  DashboardSummary,
  Event,
  ExtractedEventCandidate,
  InstagramSettings,
  PromoterSubmission,
  ScrapeStatus,
  SocialPost,
  SourceConfig,
  SourceFeed,
  Venue,
  VenueCoverage
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "";

type ApiResult<T = unknown> = {
  ok: boolean;
  data: T | null;
  message: string;
  unavailable?: boolean;
};

type SafeFetchOptions = RequestInit & {
  admin?: boolean;
  fallbackMessage?: string;
};

export type EventCreateInput = {
  title: string;
  artist?: string;
  venue_slug: string;
  starts_at: string;
  ticket_url?: string | null;
  image_url?: string | null;
  price?: string | null;
  genre?: string | null;
  notes?: string | null;
  top_pick?: boolean;
  hidden_gem?: boolean;
  cheap_gig?: boolean;
};

export type SettingsInput = Record<string, string>;

const emptyScrapeStatus: ScrapeStatus = {
  status: "never_run",
  venues_checked: 0,
  events_found: 0,
  events_created: 0,
  events_needing_review: 0,
  candidates_needing_review: 0,
  errors: [],
  warnings: []
};

async function safeFetch<T>(path: string, options: SafeFetchOptions = {}): Promise<ApiResult<T>> {
  const { admin, fallbackMessage, headers, ...init } = options;

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: init.method && init.method !== "GET" ? "no-store" : "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(admin && ADMIN_API_KEY ? { "X-Admin-Token": ADMIN_API_KEY } : {}),
        ...(headers ?? {})
      }
    });

    const data = await response.json().catch(() => null);
    if (!response.ok) {
      return {
        ok: false,
        data: null,
        message: errorMessage(data, fallbackMessage ?? `Request failed with ${response.status}`)
      };
    }

    return { ok: true, data: data as T, message: "" };
  } catch {
    return {
      ok: false,
      data: null,
      message: fallbackMessage ?? "Backend unavailable. Run backend then refresh.",
      unavailable: true
    };
  }
}

function errorMessage(data: unknown, fallback: string) {
  if (!data || typeof data !== "object") {
    return fallback;
  }
  const detail = "detail" in data ? (data as { detail?: unknown }).detail : null;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object") {
    const message = "message" in detail ? String((detail as { message?: unknown }).message ?? "") : "";
    const fix = "fix" in detail ? String((detail as { fix?: unknown }).fix ?? "") : "";
    return [message, fix].filter(Boolean).join(" ") || fallback;
  }
  if ("message" in data) {
    return String((data as { message?: unknown }).message ?? fallback);
  }
  return fallback;
}

const emptyDashboard: DashboardSummary = {
  city: "Glasgow",
  counts: {
    events: 0,
    venues: 0,
    social_posts: 0,
    needs_review: 0
  },
  next_events: []
};

const emptyCoverage: VenueCoverage = {
  city: "Glasgow",
  city_slug: "glasgow",
  summary: {
    total_venues_discovered: 0,
    venues_currently_monitored: 0,
    venues_with_successful_event_pulls: 0,
    venues_with_no_events_found: 0,
    venues_needing_manual_review: 0,
    broken_source_links: 0,
    possible_duplicates: 0,
    venues_not_checked_30_days: 0,
    automated: 0,
    manual_only: 0,
    unsupported: 0,
    coverage_score: 0,
    explanation: "Backend unavailable. Run backend then refresh.",
    missing: ["Run backend then refresh."]
  },
  discovery_sources: [],
  venues: []
};

const emptySettings: AppSettings = {
  sections: {},
  values: {
    brand_name: "Gigged Glasgow",
    tagline: "Manual-first Glasgow gig guide",
    instagram_handle: "@giggedglasgow",
    default_hashtags: "#GiggedGlasgow #GlasgowGigs #GlasgowMusic"
  },
  updated_at: null
};

export async function getDashboard(): Promise<DashboardSummary> {
  const result = await safeFetch<DashboardSummary>("/admin/dashboard?city=glasgow", {
    admin: true,
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? emptyDashboard;
}

export async function getVenues(): Promise<Venue[]> {
  const result = await safeFetch<Venue[]>("/venues?city=glasgow", {
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? [];
}

export async function getVenueCoverage(): Promise<VenueCoverage> {
  const result = await safeFetch<VenueCoverage>("/admin/venue-coverage?city=glasgow", {
    admin: true,
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? emptyCoverage;
}

export async function getEvents(): Promise<Event[]> {
  const result = await safeFetch<Event[]>("/events?city=glasgow&limit=100", {
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? [];
}

export async function getAdminEvents(view = "inbox"): Promise<AdminEvent[]> {
  const result = await safeFetch<AdminEvent[]>(`/admin/events?city=glasgow&view=${view}`, {
    admin: true,
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? [];
}

export async function getSettings(): Promise<AppSettings> {
  const result = await safeFetch<AppSettings>("/settings", {
    admin: true,
    fallbackMessage: "Backend unavailable. Settings can still be edited and retried."
  });
  return result.data ?? emptySettings;
}

export async function getAppSettings(): Promise<AppSettings> {
  return getSettings();
}

export async function saveSettings(payload: SettingsInput): Promise<ApiResult<AppSettings>> {
  const result = await safeFetch<AppSettings>("/settings", {
    method: "PATCH",
    admin: true,
    body: JSON.stringify(payload),
    fallbackMessage: "Backend unavailable. Settings were not saved."
  });
  return {
    ...result,
    message: result.ok ? "Settings saved." : result.message
  };
}

export async function createEvent(payload: EventCreateInput): Promise<ApiResult<Event>> {
  const result = await safeFetch<Event>("/events", {
    method: "POST",
    admin: true,
    body: JSON.stringify({
      city_slug: "glasgow",
      venue_slug: payload.venue_slug,
      title: payload.title,
      slug: slugify(payload.title),
      starts_at: payload.starts_at,
      ticket_url: payload.ticket_url || null,
      genre: payload.genre || null
    }),
    fallbackMessage: "Backend unavailable. Gig was not saved."
  });
  if (result.ok && result.data?.id) {
    if (payload.price || payload.notes) {
      await safeFetch<Event>(`/events/${result.data.id}`, {
        method: "PATCH",
        admin: true,
        body: JSON.stringify({
          price_min: payload.price || null,
          editorial_note: payload.notes || null
        })
      });
    }
    if (payload.top_pick) {
      await safeFetch<Event>(`/events/${result.data.id}/mark-top-pick?enabled=true`, {
        method: "POST",
        admin: true
      });
    }
  }
  const unsupported = [
    payload.artist ? "artist field" : "",
    payload.image_url ? "image URL" : "",
    payload.hidden_gem ? "hidden gem flag" : "",
    payload.cheap_gig ? "cheap gig flag" : ""
  ].filter(Boolean);
  return {
    ...result,
    message: result.ok
      ? unsupported.length
        ? `Gig saved. Future backend fields not persisted: ${unsupported.join(", ")}.`
        : "Gig saved."
      : result.message
  };
}

export async function updateEvent(eventId: number, payload: Partial<EventCreateInput>): Promise<ApiResult<Event>> {
  const result = await safeFetch<Event>(`/events/${eventId}`, {
    method: "PATCH",
    admin: true,
    body: JSON.stringify({
      title: payload.title,
      starts_at: payload.starts_at,
      ticket_url: payload.ticket_url || null,
      genre: payload.genre || null,
      editorial_note: payload.notes || null,
      price_min: payload.price || null
    }),
    fallbackMessage: "Backend unavailable. Event was not updated."
  });
  return {
    ...result,
    message: result.ok ? "Event updated." : result.message
  };
}

export async function approveEvent(eventId: number): Promise<ApiResult<Event>> {
  const result = await safeFetch<Event>(`/events/${eventId}/approve`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Event was not approved."
  });
  return { ...result, message: result.ok ? "Event approved." : result.message };
}

export async function rejectEvent(eventId: number): Promise<ApiResult<Event>> {
  const result = await safeFetch<Event>(`/events/${eventId}/reject`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Event was not rejected."
  });
  return { ...result, message: result.ok ? "Event rejected." : result.message };
}

export async function markEventTopPick(eventId: number): Promise<ApiResult<Event>> {
  const result = await safeFetch<Event>(`/events/${eventId}/mark-top-pick?enabled=true`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Event was not marked as top pick."
  });
  return { ...result, message: result.ok ? "Marked top pick." : result.message };
}

export async function markVenueChecked(venueId: number): Promise<ApiResult<Venue>> {
  const result = await safeFetch<Venue>(`/venues/${venueId}/mark-checked`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Marked checked only in this browser session."
  });
  return { ...result, message: result.ok ? "Venue marked checked." : result.message };
}

export async function runCityScrape(): Promise<ApiResult<ScrapeStatus>> {
  const result = await safeFetch<ScrapeStatus>("/admin/scrape/run?city=glasgow", {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Auto Finder did not run."
  });
  return { ...result, message: result.ok ? "Auto Finder run completed." : result.message };
}

export async function scrapeVenue(venueId: number): Promise<ApiResult<{ status: string; events_found: number }>> {
  const result = await safeFetch<{ status: string; events_found: number }>(`/admin/scrape/venues/${venueId}`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Venue auto check did not run."
  });
  return { ...result, message: result.ok ? "Venue auto check completed." : result.message };
}

export async function getScrapeStatus(): Promise<ScrapeStatus> {
  const result = await safeFetch<ScrapeStatus>("/admin/scrape/status?city=glasgow", {
    admin: true,
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? emptyScrapeStatus;
}

export async function getScrapeCandidates(): Promise<ExtractedEventCandidate[]> {
  const result = await safeFetch<ExtractedEventCandidate[]>("/admin/scrape/candidates?city=glasgow", {
    admin: true,
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? [];
}

export async function approveScrapeCandidate(candidateId: number): Promise<ApiResult<ExtractedEventCandidate>> {
  const result = await safeFetch<ExtractedEventCandidate>(`/admin/scrape/candidates/${candidateId}/approve`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Candidate was not approved."
  });
  return { ...result, message: result.ok ? "Candidate approved." : result.message };
}

export async function rejectScrapeCandidate(candidateId: number): Promise<ApiResult<ExtractedEventCandidate>> {
  const result = await safeFetch<ExtractedEventCandidate>(`/admin/scrape/candidates/${candidateId}/reject`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Candidate was not rejected."
  });
  return { ...result, message: result.ok ? "Candidate rejected." : result.message };
}

export async function convertScrapeCandidate(candidateId: number): Promise<ApiResult<Event>> {
  const result = await safeFetch<Event>(`/admin/scrape/candidates/${candidateId}/convert-to-event`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Candidate was not converted."
  });
  return { ...result, message: result.ok ? "Candidate converted to event." : result.message };
}

export async function markVenueManualOnly(venueId: number): Promise<ApiResult<Venue>> {
  const result = await safeFetch<Venue>(`/venues/${venueId}/mark-manual-only`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Venue was not marked manual-only."
  });
  return { ...result, message: result.ok ? "Venue marked manual-only." : result.message };
}

export async function updateVenueScraperConfig(
  venueId: number,
  payload: { source_mode: string; scraper_selector_config?: Record<string, unknown> | null }
): Promise<ApiResult<Venue>> {
  const result = await safeFetch<Venue>(`/venues/${venueId}`, {
    method: "PATCH",
    admin: true,
    body: JSON.stringify(payload),
    fallbackMessage: "Backend unavailable. Scraper config was not saved."
  });
  return { ...result, message: result.ok ? "Scraper config saved." : result.message };
}

export async function generateWeeklyIssue(): Promise<ApiResult<{ issue_id?: number }>> {
  const result = await safeFetch<{ issue_id?: number }>("/weekly/run?city=glasgow", {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend weekly generation unavailable. Use the frontend preview builder."
  });
  return { ...result, message: result.ok ? "Weekly issue generated." : result.message };
}

export async function getSocialPosts(status?: string): Promise<SocialPost[]> {
  const query = status ? `&status=${encodeURIComponent(status)}` : "";
  const result = await safeFetch<SocialPost[]>(`/social/posts?city=glasgow${query}`, {
    admin: true,
    fallbackMessage: "Backend unavailable. Run backend then refresh."
  });
  return result.data ?? [];
}

export async function getSocialReviewQueue(status = "review"): Promise<SocialPost[]> {
  const apiStatus = status === "review" ? "needs_review" : status;
  return getSocialPosts(apiStatus);
}

export async function exportSocialPost(postId: number): Promise<ApiResult<{ exports?: Record<string, string> }>> {
  const result = await safeFetch<{ exports?: Record<string, string> }>(`/social/posts/${postId}/export`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Copy text manually instead."
  });
  return { ...result, message: result.ok ? "Post exported." : result.message };
}

export async function markSocialPostPosted(postId: number): Promise<ApiResult<SocialPost>> {
  const result = await safeFetch<SocialPost>(`/social/posts/${postId}/mark-posted`, {
    method: "POST",
    admin: true,
    fallbackMessage: "Backend unavailable. Marked posted only in this browser session."
  });
  return { ...result, message: result.ok ? "Post marked as posted manually." : result.message };
}

export async function getInstagramSettings(): Promise<InstagramSettings> {
  const result = await safeFetch<InstagramSettings>("/admin/instagram/settings", {
    admin: true,
    fallbackMessage: "Backend unavailable. Manual export mode is assumed."
  });
  return (
    result.data ?? {
      ready: false,
      reason: "Manual export mode. Instagram automation is optional future work.",
      required_permissions: [],
      account_type: "Instagram Business or Creator account connected to a Facebook Page",
      safe_fallback: "Copy captions and post manually."
    }
  );
}

export async function getSources(): Promise<SourceConfig[]> {
  const result = await safeFetch<SourceConfig[]>("/sources", { admin: true });
  return result.data ?? [];
}

export async function getFeeds(): Promise<SourceFeed[]> {
  const result = await safeFetch<SourceFeed[]>("/feeds?city=glasgow", { admin: true });
  return result.data ?? [];
}

export async function getPromoterSubmissions(): Promise<PromoterSubmission[]> {
  const result = await safeFetch<PromoterSubmission[]>("/submissions?status=pending", { admin: true });
  return result.data ?? [];
}

export async function getCityBrands(): Promise<CityBrand[]> {
  const result = await safeFetch<CityBrand[]>("/admin/city-brands", { admin: true });
  return result.data ?? [];
}

export async function getCityTemplates(): Promise<CityTemplate[]> {
  const result = await safeFetch<CityTemplate[]>("/admin/city-templates", { admin: true });
  return result.data ?? [];
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}
