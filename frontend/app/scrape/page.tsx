import { AutoFinderClient } from "@/components/scrape/AutoFinderClient";
import { getScrapeCandidates, getScrapeStatus } from "@/lib/api";

export default async function ScrapePage() {
  const [status, candidates] = await Promise.all([getScrapeStatus(), getScrapeCandidates()]);
  return <AutoFinderClient candidates={candidates} status={status} />;
}
