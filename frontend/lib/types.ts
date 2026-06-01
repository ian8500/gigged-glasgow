export type Venue = {
  id: number;
  city_id: number;
  name: string;
  slug: string;
  address: string | null;
  postcode: string | null;
  capacity: number | null;
  website_url: string | null;
  official_website_url: string | null;
  event_listings_url: string | null;
  ticketing_url: string | null;
  official_events_url: string | null;
  feed_url: string | null;
  source_mode: string;
  robots_allowed: boolean | null;
  scraper_status: string | null;
  scraper_notes: string | null;
  scraper_selector_config: Record<string, unknown> | null;
  last_success_at: string | null;
  last_error: string | null;
  structure_changed: boolean;
  confidence_score: number;
  selector_config: Record<string, unknown> | null;
  instagram_handle: string | null;
  source_discovered_from: string | null;
  last_checked_at: string | null;
  last_event_found_at: string | null;
  status: string;
  coverage_status: string;
  notes: string | null;
  is_whitelisted: boolean;
};

export type ScrapeStatus = {
  id?: number;
  city_slug?: string;
  started_at?: string | null;
  finished_at?: string | null;
  status: string;
  venues_checked: number;
  events_found: number;
  events_created: number;
  events_needing_review: number;
  candidates_needing_review?: number;
  errors: string[];
  warnings: string[];
};

export type ExtractedEventCandidate = {
  id: number;
  venue_id: number;
  venue_name: string | null;
  city_slug: string;
  source_url: string | null;
  source_type: string;
  raw_title: string | null;
  title: string;
  artist: string | null;
  starts_at: string | null;
  price_text: string | null;
  ticket_url: string | null;
  image_url: string | null;
  confidence_score: number;
  status: "needs_review" | "approved" | "rejected" | "duplicate" | string;
  existing_event_id: number | null;
  raw_payload: Record<string, unknown> | null;
  created_at: string | null;
};

export type VenueCoverageSummary = {
  total_venues_discovered: number;
  venues_currently_monitored: number;
  venues_with_successful_event_pulls: number;
  venues_with_no_events_found: number;
  venues_needing_manual_review: number;
  broken_source_links: number;
  possible_duplicates: number;
  venues_not_checked_30_days: number;
  automated: number;
  manual_only: number;
  unsupported: number;
  api_covered_venues?: number;
  feed_covered_venues?: number;
  structured_data_venues?: number;
  selector_supported_venues?: number;
  blocked_unsupported_venues?: number;
  partner_required_venues?: number;
  sources_needing_credentials?: number;
  sources_needing_permission?: number;
  sources_failing?: number;
  sources_working?: number;
  weekly_confidence_score?: number;
  coverage_score: number;
  explanation: string;
  missing: string[];
};

export type VenueCoverageItem = {
  id: number;
  venue_name: string;
  name: string;
  slug: string;
  address: string | null;
  postcode: string | null;
  website: string | null;
  website_url: string | null;
  official_website_url: string | null;
  event_listings_url: string | null;
  official_events_url: string | null;
  feed_url: string | null;
  source_mode: string;
  robots_allowed: boolean | null;
  scraper_status?: string | null;
  scraper_notes?: string | null;
  scraper_selector_config?: Record<string, unknown> | null;
  last_success_at: string | null;
  last_error: string | null;
  structure_changed: boolean;
  confidence_score: number;
  selector_config: Record<string, unknown> | null;
  ticketing_url: string | null;
  instagram_handle: string | null;
  source_discovered_from: string | null;
  last_checked_at: string | null;
  last_event_found_at: string | null;
  status: string;
  coverage_status: string;
  notes: string | null;
  latest_check: {
    checked_at: string;
    confidence_score: number;
    events_found: number;
    message: string | null;
    structure_changed: boolean;
    diagnostic_summary?: Record<string, unknown>;
  } | null;
};

export type VenueCoverage = {
  city: string;
  city_slug: string;
  summary: VenueCoverageSummary;
  discovery_sources: Array<{
    name: string;
    url: string | null;
    mode: string;
    notes: string;
  }>;
  venues: VenueCoverageItem[];
};

export type Event = {
  id: number;
  city_id: number;
  title: string;
  slug: string;
  artist?: string | null;
  starts_at: string;
  ends_at: string | null;
  ticket_url: string | null;
  source_url?: string | null;
  image_url: string | null;
  price_min: string | null;
  price_max: string | null;
  currency: string;
  genre: string | null;
  status: string;
  confidence_score: number;
  source_attribution: string;
  needs_review: boolean;
  editorial_note?: string | null;
  top_pick?: boolean;
  hidden_gem?: boolean;
  cheap_gig?: boolean;
  venue: Venue | null;
};

export type DashboardSummary = {
  city: string;
  counts: {
    events: number;
    venues: number;
    social_posts: number;
    needs_review: number;
  };
  next_events: string[];
};

export type SocialPost = {
  id: number;
  city_id: number;
  weekly_issue_id: number | null;
  event_id: number | null;
  platform: string;
  template_name: string;
  caption: string | null;
  image_prompt: string | null;
  preview_payload: {
    title?: string;
    description?: string;
    hashtags?: string[];
    alt_text?: string;
    events?: Array<{
      event_title: string;
      artist: string;
      venue: string;
      date: string;
      door_time: string | null;
      ticket_price: string;
      ticket_link: string | null;
      source_attribution: string;
      short_description: string;
    }>;
    exports?: {
      png_path?: string;
      json_path?: string;
    };
    [key: string]: unknown;
  } | null;
  status: string;
  planned_for?: string | null;
  exported_at?: string | null;
  posted_manually_at?: string | null;
  created_at: string;
};

export type AdminEvent = {
  id: number;
  title: string;
  artist: string;
  venue: string;
  venue_slug: string | null;
  starts_at: string;
  ticket_url: string | null;
  genre: string | null;
  price_min: string | null;
  price_max: string | null;
  status: string;
  needs_review: boolean;
  confidence_score: number;
  source_attribution: string;
  editorial_note: string | null;
  top_pick: boolean;
  sponsored: boolean;
};

export type InstagramSettings = {
  ready: boolean;
  reason: string;
  required_permissions: string[];
  account_type: string;
  safe_fallback: string;
};

export type CityBrand = {
  slug: string;
  city_name: string;
  country: string;
  timezone: string;
  radius_km: number;
  weekly_roundup_start: string;
  weekly_roundup_end: string;
  brand_name: string;
  handle: string;
  tagline: string;
  colours: Record<string, string>;
  hashtags: string[];
  voice_notes: string[];
  default_posting_schedule: Record<string, string>;
};

export type CityTemplate = CityBrand & {
  venues: Array<{ name: string; slug: string }>;
  coordinates: { latitude: number; longitude: number };
  genre_filters: string[];
  minimum_date_range_days: number;
};

export type AppSettingField = {
  key: string;
  label: string;
  section: string;
  secret: boolean;
  configured: boolean;
  value: string;
  source: string;
  env_name: string | null;
};

export type AppSettings = {
  sections: Record<string, AppSettingField[]>;
  values: Record<string, string>;
  updated_at: string | null;
};

export type SourceConfig = {
  id: number;
  name: string;
  slug: string | null;
  kind: string;
  base_url: string | null;
  terms_url: string | null;
  is_enabled: boolean;
  notes: string | null;
  requires_credentials: boolean;
  required_settings: string[];
  official_api_available: string | null;
  current_mode: string | null;
  terms_reviewed: boolean;
  automation_allowed: string | null;
  limitations: string | null;
  admin_url: string | null;
  health: {
    status: string;
    last_tested_at: string | null;
    last_success_at: string | null;
    last_ingest_at: string | null;
    last_error: string | null;
    configured: boolean;
    enabled: boolean;
    events_last_found: number;
    warnings: string[];
  };
  created_at: string | null;
};

export type SourceFeed = {
  id: number;
  source_name: string;
  venue_id: number | null;
  city_slug: string;
  feed_url: string;
  feed_type: string;
  enabled: boolean;
  last_checked_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  notes: string | null;
};

export type PromoterSubmission = {
  id: number;
  event_title: string;
  artist: string;
  venue: string;
  date: string;
  time: string;
  ticket_url: string;
  price: string | null;
  promoter_contact_email: string;
  image_upload_url: string | null;
  notes: string | null;
  status: string;
  created_at: string | null;
};
