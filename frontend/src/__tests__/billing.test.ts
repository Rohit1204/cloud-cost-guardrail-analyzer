import { describe, expect, it } from "vitest";
import { estimateBilling } from "@/lib/billing";
import { costSummaryFixture } from "@/test/fixtures";

describe("estimateBilling", () => {
  it("projects current month charges and reminder details", () => {
    const estimate = estimateBilling(costSummaryFixture.cost_summary, new Date("2026-04-24T00:00:00Z"));

    expect(estimate?.monthToDateCost).toBe(12.34);
    expect(estimate?.projectedMonthEndCost).toBeGreaterThan(12.34);
    expect(estimate?.daysRemaining).toBeGreaterThan(0);
    expect(estimate?.topServices[0].service).toContain("Elastic Compute");
  });

  it("returns null when cost summary is unavailable", () => {
    expect(estimateBilling(null)).toBeNull();
  });
});
