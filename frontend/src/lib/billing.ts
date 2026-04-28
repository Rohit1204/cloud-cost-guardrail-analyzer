import type { CostSummary, ServiceCost } from "./types";

export type BillingEstimate = {
  currency: string;
  billingPeriodStart: string;
  billingPeriodEnd: string;
  monthToDateCost: number;
  projectedMonthEndCost: number;
  daysElapsed: number;
  daysRemaining: number;
  reminderLevel: "info" | "warning";
  reminderText: string;
  topServices: ServiceCost[];
};

function daysBetween(start: Date, end: Date): number {
  const msPerDay = 1000 * 60 * 60 * 24;
  return Math.max(1, Math.ceil((end.getTime() - start.getTime()) / msPerDay));
}

function monthEndExclusive(start: Date): Date {
  return new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1));
}

export function estimateBilling(summary: CostSummary | null | undefined, now = new Date()): BillingEstimate | null {
  if (!summary || summary.monthly_costs.length === 0) {
    return null;
  }

  const currentMonth = summary.monthly_costs[summary.monthly_costs.length - 1];
  const periodStart = new Date(`${currentMonth.start}T00:00:00Z`);
  const reportedEnd = new Date(`${currentMonth.end}T00:00:00Z`);
  const periodEnd = monthEndExclusive(periodStart);
  const effectiveEnd = reportedEnd < periodEnd ? reportedEnd : periodEnd;
  const daysElapsed = daysBetween(periodStart, effectiveEnd);
  const totalDays = daysBetween(periodStart, periodEnd);
  const daysRemaining = Math.max(0, daysBetween(now, periodEnd) - 1);
  const projectedMonthEndCost = (currentMonth.amount / daysElapsed) * totalDays;
  const reminderLevel = daysRemaining <= 7 ? "warning" : "info";

  return {
    currency: summary.currency,
    billingPeriodStart: currentMonth.start,
    billingPeriodEnd: periodEnd.toISOString().slice(0, 10),
    monthToDateCost: currentMonth.amount,
    projectedMonthEndCost,
    daysElapsed,
    daysRemaining,
    reminderLevel,
    reminderText:
      daysRemaining <= 7
        ? `Billing period closes in ${daysRemaining} day${daysRemaining === 1 ? "" : "s"}. Review spend and payment method now.`
        : `Billing period closes in ${daysRemaining} days. Keep monitoring before the final AWS invoice is generated.`,
    topServices: summary.top_services.slice(0, 5),
  };
}
