export type Venue = {
  id: number;
  city_id: number;
  name: string;
  slug: string;
  address: string | null;
  postcode: string | null;
  capacity: number | null;
  website_url: string | null;
  event_listings_url: string | null;
  ticketing_url: string | null;
  instagram_handle: string | null;
  source_discovered_from: string | null;
  last_checked_at: string | null;
  last_event_found_at: string | null;
  status: string;
  coverage_status: string;
  notes: string | null;
  is_whitelisted: boolean;
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
  event_listings_url: string | null;
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
  starts_at: string;
  ends_at: string | null;
  ticket_url: string | null;
  image_url: string | null;
  price_min: string | null;
  price_max: string | null;
  currency: string;
  genre: string | null;
  status: string;
  confidence_score: number;
  source_attribution: string;
  needs_review: boolean;
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
  kind: string;
  base_url: string | null;
  terms_url: string | null;
  is_enabled: boolean;
  notes: string | null;
  created_at: string | null;
};
