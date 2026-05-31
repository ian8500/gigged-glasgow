export const brand = {
  name: "Gigged Glasgow",
  tagline: "Your weekly Glasgow gig radar.",
  personality: [
    "Glasgow-focused",
    "energetic",
    "local",
    "slightly underground",
    "trustworthy",
    "music-first",
    "scalable"
  ],
  colors: {
    ink: "#0e0e10",
    night: "#17151d",
    asphalt: "#25232b",
    rail: "#393642",
    paper: "#f3efe4",
    bone: "#fff8e8",
    acid: "#d6f84c",
    clyde: "#28b8a7",
    poster: "#ef4d2f",
    plum: "#7b4aa0",
    tenement: "#d987a1",
    amber: "#f6b33d"
  },
  typography: {
    display: "Arial Black / Impact",
    sans: "Arial / Helvetica",
    editorial: "Georgia"
  },
  voice: {
    headline: "Short, useful, confident. No forced slang.",
    caption: "Venue-first detail, clear timing, useful price signals.",
    cityScale: "Replace the city wordmark and local whitelist while preserving the GG-style radar system."
  }
};

export const socialTemplates = [
  {
    key: "weekly-roundup",
    name: "Weekly roundup",
    label: "Fri to Thu",
    title: "Glasgow gigs worth knowing",
    kicker: "Your weekly radar",
    accent: "acid",
    description: "Primary weekly editorial post."
  },
  {
    key: "carousel",
    name: "Carousel",
    label: "5 slides",
    title: "This week, sorted",
    kicker: "Save this",
    accent: "clyde",
    description: "Multi-slide guide for ranked recommendations."
  },
  {
    key: "tonight",
    name: "Tonight in Glasgow",
    label: "Tonight",
    title: "3 gigs for tonight",
    kicker: "Last-minute radar",
    accent: "poster",
    description: "Same-day utility post."
  },
  {
    key: "under-15",
    name: "Under £15",
    label: "Budget",
    title: "Under £15, still loud",
    kicker: "Low-cost picks",
    accent: "amber",
    description: "Price-led discovery format."
  },
  {
    key: "hidden-gem",
    name: "Hidden gem",
    label: "Small room",
    title: "Small room, big reason",
    kicker: "Worth the walk",
    accent: "tenement",
    description: "Underground discovery post."
  },
  {
    key: "big-one",
    name: "Big one this week",
    label: "Spotlight",
    title: "The big one this week",
    kicker: "Main pick",
    accent: "plum",
    description: "Single-event hero post."
  }
] as const;

export type SocialTemplateKey = (typeof socialTemplates)[number]["key"];
