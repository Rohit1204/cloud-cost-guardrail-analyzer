import type { CostSummary, Finding, Recommendation } from "./types";

const EPS = 1e-9;

export function countServicesWithSpend(summary: CostSummary | null | undefined): number {
  if (!summary?.top_services?.length) {
    return 0;
  }
  return summary.top_services.filter((s) => s.amount > EPS).length;
}

export function countRegionsFromRecommendations(recommendations: Recommendation[] | null | undefined): number {
  if (!recommendations?.length) {
    return 0;
  }
  return new Set(recommendations.map((r) => r.finding.region).filter(Boolean)).size;
}

export function countFindingRegions(findings: Finding[] | null | undefined): number {
  if (!findings?.length) {
    return 0;
  }
  return new Set(findings.map((f) => f.region).filter(Boolean)).size;
}

/** Compare last two monthly buckets in the loaded window (not calendar-aligned to “same day” like AWS). */
export function priorMonthDeltaLabel(summary: CostSummary | null | undefined): string | null {
  const pts = summary?.monthly_costs;
  if (!pts || pts.length < 2) {
    return null;
  }
  const cur = pts[pts.length - 1]?.amount ?? 0;
  const prev = pts[pts.length - 2]?.amount ?? 0;
  if (Math.abs(cur) < EPS && Math.abs(prev) < EPS) {
    return null;
  }
  if (prev <= EPS) {
    return cur > EPS ? "Up vs prior month in this window" : null;
  }
  const pct = ((cur - prev) / prev) * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}% vs prior month in this window`;
}
