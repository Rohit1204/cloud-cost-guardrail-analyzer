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

  it("uses month_to_date_unblended_cost when the last monthly bucket amount is stale", () => {
    const summary = {
      ...costSummaryFixture.cost_summary!,
      month_to_date_unblended_cost: 104.5,
      monthly_costs: [{ start: "2026-04-01", end: "2026-04-29", amount: 0, currency: "INR" }],
    };
    const estimate = estimateBilling(summary, new Date("2026-04-24T00:00:00Z"));
    expect(estimate?.monthToDateCost).toBe(104.5);
  });
});
