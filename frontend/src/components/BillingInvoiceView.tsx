"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import { useState } from "react";
import { ApiError, getBillingConsoleUrl } from "@/lib/api";
import type { CostSummary } from "@/lib/types";
import { estimateBilling } from "@/lib/billing";
import { formatDate, formatMoney } from "@/lib/format";
import { Badge, Card, EmptyBlock, SectionHeader } from "./ui";

const AWS_BILLING_HOME = "https://console.aws.amazon.com/billing/home";

type Props = {
  summary: CostSummary | null | undefined;
};

export function BillingInvoiceView({ summary }: Props) {
  const estimate = estimateBilling(summary);
  const [federatedLoading, setFederatedLoading] = useState(false);
  const [federatedError, setFederatedError] = useState<string | null>(null);

  async function openBillingConsole() {
    setFederatedError(null);
    setFederatedLoading(true);
    try {
      const { url } = await getBillingConsoleUrl();
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        window.open(AWS_BILLING_HOME, "_blank", "noopener,noreferrer");
      } else {
        const message = e instanceof Error ? e.message : "Could not open the billing console.";
        setFederatedError(message);
      }
    } finally {
      setFederatedLoading(false);
    }
  }

  if (!estimate) {
    return <EmptyBlock title="No invoice estimate yet" detail="Cost Explorer data is required to estimate the current billing period." />;
  }

  return (
    <Card>
      <SectionHeader
        eyebrow="Billing"
        title="Invoice estimate"
        action={
          <button
            className="inline-flex items-center rounded-2xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={federatedLoading}
            onClick={() => void openBillingConsole()}
            type="button"
          >
            {federatedLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : null}
            Open AWS Billing Console
            <ExternalLink className="ml-2 h-4 w-4" aria-hidden />
          </button>
        }
      />

      {federatedError ? (
        <div className="mb-3 space-y-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <p>{federatedError}</p>
          <p>
            <a className="font-semibold underline" href={AWS_BILLING_HOME} rel="noreferrer" target="_blank">
              Open Billing home with your own AWS login
            </a>
          </p>
        </div>
      ) : null}

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
      <p className="mt-2 text-xs leading-5 text-slate-500">
        This button uses federated console sign-in when your deployment sets{" "}
        <code className="rounded bg-slate-100 px-1 py-0.5 text-[0.7rem]">BILLING_CONSOLE_ROLE_ARN</code>. If that is not configured, the same
        button opens the standard Billing home for whatever AWS identity your browser already has. Anyone who can use this dashboard can use a
        federated session when it is enabled.
      </p>
    </Card>
  );
}
