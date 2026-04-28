import { ExternalLink } from "lucide-react";
import type { CostSummary } from "@/lib/types";
import { estimateBilling } from "@/lib/billing";
import { formatDate, formatMoney } from "@/lib/format";
import { Badge, Card, EmptyBlock, SectionHeader } from "./ui";

type Props = {
  summary: CostSummary | null | undefined;
};

export function BillingInvoiceView({ summary }: Props) {
  const estimate = estimateBilling(summary);

  if (!estimate) {
    return <EmptyBlock title="No invoice estimate yet" detail="Cost Explorer data is required to estimate the current billing period." />;
  }

  return (
    <Card>
      <SectionHeader
        eyebrow="Billing"
        title="Invoice estimate"
        action={
          <a
            className="inline-flex items-center rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:text-blue-700"
            href="https://console.aws.amazon.com/billing/home"
            rel="noreferrer"
            target="_blank"
          >
            Open AWS Billing
            <ExternalLink className="ml-2 h-4 w-4" />
          </a>
        }
      />

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={estimate.reminderLevel === "warning" ? "amber" : "blue"}>Billing reminder</Badge>
          <p className="text-sm font-medium text-slate-700">{estimate.reminderText}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Current estimated charges</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{formatMoney(estimate.monthToDateCost, estimate.currency)}</p>
          <p className="mt-1 text-xs text-slate-500">
            {formatDate(estimate.billingPeriodStart)} to {formatDate(summary?.period.end)}
          </p>
        </div>
        <div className="rounded-2xl bg-blue-50 p-4">
          <p className="text-sm text-blue-700">Projected month-end</p>
          <p className="mt-2 text-2xl font-semibold text-blue-950">{formatMoney(estimate.projectedMonthEndCost, estimate.currency)}</p>
          <p className="mt-1 text-xs text-blue-700">
            Based on {estimate.daysElapsed} day{estimate.daysElapsed === 1 ? "" : "s"} of current-month usage
          </p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-sm font-semibold text-slate-900">Estimated charge drivers</p>
        <div className="mt-3 space-y-2">
          {estimate.topServices.map((service) => (
            <div className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2 text-sm" key={service.service}>
              <span className="min-w-0 truncate text-slate-700">{service.service}</span>
              <span className="font-semibold text-slate-950">{formatMoney(service.amount, service.currency)}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-4 text-xs leading-5 text-slate-500">
        This is an estimate from Cost Explorer usage data, not the final AWS invoice. AWS finalizes invoices in the Billing Console after the billing
        period closes.
      </p>
    </Card>
  );
}
