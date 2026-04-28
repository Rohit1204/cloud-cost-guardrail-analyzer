"use client";

import { RefreshCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useCostSummary, useHealth, useRecommendations } from "@/hooks/useGuardrailApi";
import { getApiBaseUrl } from "@/lib/api";
import { AlertRunner } from "./AlertRunner";
import { CostCharts } from "./CostCharts";
import { DetectorErrors } from "./DetectorErrors";
import { RecommendationsList } from "./RecommendationsList";
import { SummaryCards } from "./SummaryCards";
import { Badge, Card, ErrorBlock, LoadingBlock, SectionHeader } from "./ui";

const MONTH_OPTIONS = [1, 3, 6, 12];

export function Dashboard() {
  const [months, setMonths] = useState(6);
  const health = useHealth();
  const costs = useCostSummary(months);
  const recommendations = useRecommendations(months);

  const allErrors = useMemo(
    () => [...(costs.data?.errors ?? []), ...(recommendations.data?.errors ?? [])],
    [costs.data?.errors, recommendations.data?.errors],
  );

  function refreshAll() {
    health.reload();
    costs.reload();
    recommendations.reload();
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="rounded-[2rem] border border-slate-200 bg-white/80 p-6 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={health.data?.status === "ok" ? "green" : "amber"}>{health.data?.status ?? "checking backend"}</Badge>
              <Badge>{health.data?.target_region ?? "ap-south-1"}</Badge>
            </div>
            <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Cloud cost guardrail dashboard
            </h1>
            <p className="mt-3 max-w-2xl text-base text-slate-600">
              Analyze AWS spend, surface idle resources, and send owner-aware Gmail or WhatsApp alerts from one responsive frontend.
            </p>
            <p className="mt-3 text-xs text-slate-500">API: {getApiBaseUrl()}</p>
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
              Refresh
            </button>
          </div>
        </div>
      </header>

      {health.error ? <ErrorBlock message={health.error} onRetry={health.reload} /> : null}

      <SummaryCards costSummary={costs.data?.cost_summary} health={health.data} recommendations={recommendations.data} />

      <DetectorErrors errors={allErrors} />

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
            <SectionHeader eyebrow="Readiness" title="Integration status" />
            <div className="space-y-3 text-sm text-slate-600">
              <p>Gmail token: {health.data?.gmail_token_configured ? "Configured" : "Missing"}</p>
              <p>Default Gmail recipient: {health.data?.gmail_recipient_configured ? "Configured" : "Missing"}</p>
              <p>WhatsApp: {health.data?.whatsapp_configured ? "Configured" : "Missing"}</p>
            </div>
          </Card>
        </section>
      </div>
    </main>
  );
}
