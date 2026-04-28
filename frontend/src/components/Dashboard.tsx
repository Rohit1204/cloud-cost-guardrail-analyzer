"use client";

import { RefreshCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useCostSummary, useHealth, useRecommendations } from "@/hooks/useGuardrailApi";
import { AlertRunner } from "./AlertRunner";
import { BillingInvoiceView } from "./BillingInvoiceView";
import { CostCharts } from "./CostCharts";
import { DetectorErrors } from "./DetectorErrors";
import { RecommendationsList } from "./RecommendationsList";
import { SummaryCards } from "./SummaryCards";
import { Badge, Card, ErrorBlock, LoadingBlock, SectionHeader } from "./ui";
import type { AuthUser } from "@/lib/auth";

const MONTH_OPTIONS = [1, 3, 6, 12];

export function Dashboard({ user, onSignOut }: { user: AuthUser; onSignOut: () => void }) {
  const [months, setMonths] = useState(6);
  const health = useHealth();
  const costs = useCostSummary(months);
  const recommendations = useRecommendations(months);
  const isLoadingData = costs.loading || recommendations.loading;
  const hasLiveData = Boolean(costs.data || recommendations.data);
  const hasDataError = Boolean((costs.error || recommendations.error) && !hasLiveData);

  const allErrors = useMemo(
    () => [...(costs.data?.errors ?? []), ...(recommendations.data?.errors ?? [])],
    [costs.data?.errors, recommendations.data?.errors],
  );

  function refreshAll() {
    costs.reload();
    recommendations.reload();
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="rounded-[2rem] border border-slate-200 bg-white/80 p-6 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold transition ${
                  hasLiveData
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                    : hasDataError
                      ? "border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
                      : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
                }`}
                onClick={refreshAll}
                type="button"
              >
                <span
                  className={`mr-2 h-2 w-2 rounded-full ${
                    hasLiveData ? "bg-emerald-500" : hasDataError ? "bg-red-500" : "bg-amber-500"
                  }`}
                />
                {isLoadingData ? "Loading data" : hasLiveData ? "Live data" : hasDataError ? "Data unavailable" : "Load data"}
              </button>
              <Badge>{months}-month view</Badge>
              <Badge>{user.email}</Badge>
            </div>
            <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Cloud cost guardrail dashboard
            </h1>
            <p className="mt-3 max-w-2xl text-base text-slate-600">
              Analyze AWS spend, surface idle resources, and send owner-aware Gmail or WhatsApp alerts from one responsive frontend.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:items-center">
            <select
              aria-label="Cost analysis window"
              className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20"
              onChange={(event) => setMonths(Number(event.target.value))}
              value={months}
            >
              {MONTH_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  Last {option} {option === 1 ? "month" : "months"}
                </option>
              ))}
            </select>
            <button
              className="inline-flex items-center justify-center rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
              onClick={refreshAll}
              type="button"
            >
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh data
            </button>
            <button
              className="inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
              onClick={onSignOut}
              type="button"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <SummaryCards costSummary={costs.data?.cost_summary} health={health.data} recommendations={recommendations.data} />

      <DetectorErrors errors={allErrors} />

      <BillingInvoiceView summary={costs.data?.cost_summary} />

      <section>
        <SectionHeader eyebrow="Analyze" title="Cost analyzer" />
        {costs.loading ? <LoadingBlock label="Loading cost summary" /> : null}
        {costs.error ? <ErrorBlock message={costs.error} onRetry={costs.reload} /> : null}
        {!costs.loading && !costs.error ? <CostCharts summary={costs.data?.cost_summary} /> : null}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <section>
          {recommendations.loading ? <LoadingBlock label="Loading recommendations" /> : null}
          {recommendations.error ? <ErrorBlock message={recommendations.error} onRetry={recommendations.reload} /> : null}
          {!recommendations.loading && !recommendations.error ? (
            <RecommendationsList recommendations={recommendations.data?.recommendations ?? []} />
          ) : null}
        </section>

        <section className="space-y-6">
          <AlertRunner months={months} />
          <Card>
            <SectionHeader
              action={
                <button
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                  onClick={health.reload}
                  type="button"
                >
                  {health.loading ? "Checking..." : "Check integrations"}
                </button>
              }
              eyebrow="Readiness"
              title="Integration status"
            />
            {health.error ? <ErrorBlock message={health.error} onRetry={health.reload} /> : null}
            <div className="space-y-3 text-sm text-slate-600">
              <p>Gmail token: {health.data ? (health.data.gmail_token_configured ? "Configured" : "Missing") : "Not checked"}</p>
              <p>Default Gmail recipient: {health.data ? (health.data.gmail_recipient_configured ? "Configured" : "Missing") : "Not checked"}</p>
              <p>WhatsApp: {health.data ? (health.data.whatsapp_configured ? "Configured" : "Missing") : "Not checked"}</p>
            </div>
          </Card>
        </section>
      </div>
    </main>
  );
}
