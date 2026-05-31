import type {
  AdminEvent,
  AppSettings,
  CityBrand,
  CityTemplate,
  DashboardSummary,
  Event,
  InstagramSettings,
  SocialPost,
  SourceConfig,
  Venue,
  VenueCoverage
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "change-me-in-production";

async function apiGet<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      next: { revalidate: 30 },
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      }
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getDashboard(): Promise<DashboardSummary> {
  const data = await apiGet<DashboardSummary>("/dashboard/summary?city=glasgow", {
    headers: { "X-Admin-Token": ADMIN_API_KEY }
  });

  return (
    data ?? {
      city: "Glasgow",
      counts: {
        events: 0,
        venues: 0,
        social_posts: 0,
        needs_review: 0
      },
      next_events: []
    }
  );
}

export async function getVenues(): Promise<Venue[]> {
  return (await apiGet<Venue[]>("/venues?city=glasgow")) ?? [];
}

export async function getVenueCoverage(): Promise<VenueCoverage> {
  return (
    (await apiGet<VenueCoverage>("/admin/venue-coverage?city=glasgow", {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? {
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
        explanation: "Backend unavailable; start FastAPI and seed Glasgow coverage.",
        missing: ["Run backend seed and venue coverage checks."]
      },
      discovery_sources: [],
      venues: []
    }
  );
}

export async function getEvents(): Promise<Event[]> {
  return (await apiGet<Event[]>("/events?city=glasgow&limit=20")) ?? [];
}

export async function getSocialReviewQueue(status = "review"): Promise<SocialPost[]> {
  const apiStatus = status === "review" ? "needs_review" : status;
  return (
    (await apiGet<SocialPost[]>(`/social/posts?city=glasgow&status=${apiStatus}`, {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? []
  );
}

export async function getAdminEvents(view = "inbox"): Promise<AdminEvent[]> {
  return (
    (await apiGet<AdminEvent[]>(`/admin/events?city=glasgow&view=${view}`, {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? []
  );
}

export async function getInstagramSettings(): Promise<InstagramSettings> {
  return (
    (await apiGet<InstagramSettings>("/admin/instagram/settings", {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? {
      ready: false,
      reason: "Backend unavailable; manual export mode is assumed.",
      required_permissions: [
        "instagram_basic",
        "instagram_content_publish",
        "pages_show_list",
        "pages_read_engagement"
      ],
      account_type: "Instagram Business or Creator account connected to a Facebook Page",
      safe_fallback: "Export PNG plus caption and post manually."
    }
  );
}

export async function getAppSettings(): Promise<AppSettings> {
  return (
    (await apiGet<AppSettings>("/settings", {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? { sections: {}, values: {}, updated_at: null }
  );
}

export async function getSources(): Promise<SourceConfig[]> {
  return (
    (await apiGet<SourceConfig[]>("/sources", {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? []
  );
}

export async function getCityBrands(): Promise<CityBrand[]> {
  return (
    (await apiGet<CityBrand[]>("/admin/city-brands", {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? []
  );
}

export async function getCityTemplates(): Promise<CityTemplate[]> {
  return (
    (await apiGet<CityTemplate[]>("/admin/city-templates", {
      headers: { "X-Admin-Token": ADMIN_API_KEY }
    })) ?? []
  );
}
