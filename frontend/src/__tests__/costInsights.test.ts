import { describe, expect, it } from "vitest";
import {
  countFindingRegions,
  countRegionsFromRecommendations,
  countServicesWithSpend,
  priorMonthDeltaLabel,
} from "@/lib/costInsights";
import type { CostSummary, Finding, Recommendation } from "@/lib/types";

describe("costInsights", () => {
  it("counts services with positive spend", () => {
    const summary = {
      months: 1,
      period: { start: "2026-05-01", end: "2026-05-14" },
      total_unblended_cost: 0,
      month_to_date_unblended_cost: 0,
      currency: "USD",
      monthly_costs: [],
      top_services: [
        { service: "AWS Lambda", amount: 0.0001, currency: "USD" },
        { service: "S3", amount: 0, currency: "USD" },
      ],
    } as CostSummary;
    expect(countServicesWithSpend(summary)).toBe(1);
  });

  it("counts unique finding regions from raw findings list", () => {
    const findings: Finding[] = [
      {
        category: "x",
        resource_id: "1",
        resource_type: "t",
        region: "ap-south-1",
        title: "a",
        description: "d",
        metric_name: "m",
        metric_value: 1,
        threshold: 0,
        metadata: {},
      },
      {
        category: "x",
        resource_id: "2",
        resource_type: "t",
        region: "us-east-1",
        title: "b",
        description: "d",
        metric_name: "m",
        metric_value: 1,
        threshold: 0,
        metadata: {},
      },
      {
        category: "x",
        resource_id: "3",
        resource_type: "t",
        region: "ap-south-1",
        title: "c",
        description: "d",
        metric_name: "m",
        metric_value: 1,
        threshold: 0,
        metadata: {},
      },
    ];
    expect(countFindingRegions(findings)).toBe(2);
  });

  it("counts unique regions from recommendations", () => {
    const f1: Finding = {
      category: "x",
      resource_id: "1",
      resource_type: "t",
      region: "ap-south-1",
      title: "a",
      description: "d",
      metric_name: "m",
      metric_value: 1,
      threshold: 0,
      metadata: {},
    };
    const f2: Finding = {
      category: "x",
      resource_id: "3",
      resource_type: "t",
      region: "ap-south-1",
      title: "c",
      description: "d",
      metric_name: "m",
      metric_value: 1,
      threshold: 0,
      metadata: {},
    };
    const recs = [
      {
        recommendation_id: "1",
        status: "new" as const,
        finding: f1,
        priority: "info",
        action: "",
        rationale: "",
        next_steps: [],
      },
      {
        recommendation_id: "2",
        status: "new" as const,
        finding: f2,
        priority: "info",
        action: "",
        rationale: "",
        next_steps: [],
      },
    ] as Recommendation[];
    expect(countRegionsFromRecommendations(recs)).toBe(1);
  });

  it("returns month-over-month label when two buckets exist", () => {
    const summary = {
      months: 2,
      period: { start: "2026-04-01", end: "2026-05-14" },
      total_unblended_cost: 0,
      month_to_date_unblended_cost: 0,
      currency: "USD",
      monthly_costs: [
        { start: "2026-04-01", end: "2026-05-01", amount: 100, currency: "USD" },
        { start: "2026-05-01", end: "2026-05-14", amount: 50, currency: "USD" },
      ],
      top_services: [],
    } as CostSummary;
    expect(priorMonthDeltaLabel(summary)).toBe("-50.0% vs prior month in this window");
  });
});
