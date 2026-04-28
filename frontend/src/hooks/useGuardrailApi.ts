"use client";

import { getCostSummary, getHealth, getRecommendations } from "@/lib/api";
import type { CostSummaryResponse, HealthResponse, RecommendationsResponse } from "@/lib/types";
import { useApiResource } from "./useApiResource";

export function useHealth() {
  return useApiResource<HealthResponse>((signal) => getHealth(signal), []);
}

export function useCostSummary(months: number) {
  return useApiResource<CostSummaryResponse>((signal) => getCostSummary(months, signal), [months]);
}

export function useRecommendations(months: number) {
  return useApiResource<RecommendationsResponse>((signal) => getRecommendations(months, signal), [months]);
}
