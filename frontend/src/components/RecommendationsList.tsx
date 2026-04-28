"use client";

import { useMemo, useState } from "react";
import { updateRecommendationStatus } from "@/lib/api";
import type { Recommendation, RecommendationStatus } from "@/lib/types";
import { formatMoney, metadataValue, sentenceCase } from "@/lib/format";
import { Badge, Card, EmptyBlock, SectionHeader } from "./ui";

function priorityTone(priority: string): "red" | "amber" | "blue" | "slate" {
  if (priority === "critical") {
    return "red";
  }
  if (priority === "warning") {
    return "amber";
  }
  if (priority === "info") {
    return "blue";
  }
  return "slate";
}

const STATUS_OPTIONS: { value: RecommendationStatus; label: string }[] = [
  { value: "new", label: "New" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "in_progress", label: "In Progress" },
  { value: "resolved", label: "Resolved" },
];

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

export function RecommendationsList({ recommendations }: { recommendations: Recommendation[] }) {
  const [statusOverrides, setStatusOverrides] = useState<Record<string, RecommendationStatus>>({});
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");
  const [owner, setOwner] = useState("all");
  const [environment, setEnvironment] = useState("all");
  const [category, setCategory] = useState("all");
  const [minSavings, setMinSavings] = useState("");
  const [statusError, setStatusError] = useState<string | null>(null);

  const items = useMemo(
    () =>
      recommendations.map((recommendation) => ({
        ...recommendation,
        status: statusOverrides[recommendation.recommendation_id] ?? recommendation.status,
      })),
    [recommendations, statusOverrides],
  );

  const filterOptions = useMemo(
    () => ({
      severities: unique(items.map((recommendation) => recommendation.priority)),
      owners: unique(items.map((recommendation) => metadataValue(recommendation.finding.metadata, "owner") ?? "Unassigned")),
      environments: unique(items.map((recommendation) => metadataValue(recommendation.finding.metadata, "environment") ?? "Unknown environment")),
      categories: unique(items.map((recommendation) => recommendation.finding.category)),
    }),
    [items],
  );

  const filteredRecommendations = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    const minSavingsValue = minSavings ? Number(minSavings) : null;

    return items.filter((recommendation) => {
      const itemOwner = metadataValue(recommendation.finding.metadata, "owner") ?? "Unassigned";
      const itemEnvironment = metadataValue(recommendation.finding.metadata, "environment") ?? "Unknown environment";
      const savings = recommendation.finding.estimated_monthly_savings ?? 0;
      const searchable = [
        recommendation.finding.title,
        recommendation.finding.description,
        recommendation.finding.resource_id,
        recommendation.finding.resource_type,
        recommendation.finding.category,
        itemOwner,
        itemEnvironment,
        recommendation.action,
        recommendation.rationale,
      ]
        .join(" ")
        .toLowerCase();

      return (
        (severity === "all" || recommendation.priority === severity) &&
        (status === "all" || recommendation.status === status) &&
        (owner === "all" || itemOwner === owner) &&
        (environment === "all" || itemEnvironment === environment) &&
        (category === "all" || recommendation.finding.category === category) &&
        (!normalizedSearch || searchable.includes(normalizedSearch)) &&
        (minSavingsValue === null || savings >= minSavingsValue)
      );
    });
  }, [category, environment, items, minSavings, owner, search, severity, status]);

  async function changeStatus(recommendation: Recommendation, nextStatus: RecommendationStatus) {
    const previousOverrides = statusOverrides;
    setStatusError(null);
    setStatusOverrides((current) => ({ ...current, [recommendation.recommendation_id]: nextStatus }));

    try {
      await updateRecommendationStatus({ recommendation_id: recommendation.recommendation_id, status: nextStatus });
    } catch (caught) {
      setStatusOverrides(previousOverrides);
      setStatusError(caught instanceof Error ? caught.message : "Unable to update recommendation status");
    }
  }

  if (recommendations.length === 0) {
    return <EmptyBlock title="No recommendations" detail="No actionable findings crossed your configured thresholds." />;
  }

  return (
    <Card>
      <SectionHeader eyebrow="Actions" title="Recommended guardrails" />
      <div className="mb-4 grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2 xl:grid-cols-3">
        <input
          aria-label="Search recommendations"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search resource, owner, action..."
          value={search}
        />
        <select
          aria-label="Severity filter"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setSeverity(event.target.value)}
          value={severity}
        >
          <option value="all">All severities</option>
          {filterOptions.severities.map((option) => (
            <option key={option} value={option}>
              {sentenceCase(option)}
            </option>
          ))}
        </select>
        <select
          aria-label="Status filter"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setStatus(event.target.value)}
          value={status}
        >
          <option value="all">All statuses</option>
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Owner filter"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setOwner(event.target.value)}
          value={owner}
        >
          <option value="all">All owners</option>
          {filterOptions.owners.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          aria-label="Environment filter"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setEnvironment(event.target.value)}
          value={environment}
        >
          <option value="all">All environments</option>
          {filterOptions.environments.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          aria-label="Service category filter"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setCategory(event.target.value)}
          value={category}
        >
          <option value="all">All services/categories</option>
          {filterOptions.categories.map((option) => (
            <option key={option} value={option}>
              {sentenceCase(option)}
            </option>
          ))}
        </select>
        <input
          aria-label="Minimum estimated savings"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          min="0"
          onChange={(event) => setMinSavings(event.target.value)}
          placeholder="Min estimated savings"
          type="number"
          value={minSavings}
        />
      </div>
      {statusError ? <p className="mb-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{statusError}</p> : null}
      {filteredRecommendations.length === 0 ? (
        <EmptyBlock title="No matching recommendations" detail="Adjust filters or search to see more guardrail actions." />
      ) : null}
      <div className="space-y-4">
        {filteredRecommendations.map((recommendation) => {
          const owner = metadataValue(recommendation.finding.metadata, "owner") ?? "Unassigned";
          const environment = metadataValue(recommendation.finding.metadata, "environment") ?? "Unknown environment";
          const savings = recommendation.finding.estimated_monthly_savings;

          return (
            <article className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4" key={`${recommendation.finding.category}-${recommendation.finding.resource_id}`}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone={priorityTone(recommendation.priority)}>{sentenceCase(recommendation.priority)}</Badge>
                    <Badge tone="blue">{STATUS_OPTIONS.find((option) => option.value === recommendation.status)?.label ?? sentenceCase(recommendation.status)}</Badge>
                    <Badge>{sentenceCase(recommendation.finding.category)}</Badge>
                    <Badge tone="green">{environment}</Badge>
                  </div>
                  <h3 className="mt-3 text-base font-semibold text-slate-950">{recommendation.finding.title}</h3>
                  <p className="mt-1 text-sm text-slate-600">{recommendation.finding.description}</p>
                </div>
                {typeof savings === "number" ? (
                  <div className="rounded-2xl bg-white px-4 py-3 text-right shadow-sm">
                    <p className="text-xs text-slate-500">Est. savings</p>
                    <p className="font-semibold text-emerald-700">{formatMoney(savings)}</p>
                  </div>
                ) : null}
              </div>

              <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                <p>
                  <span className="font-semibold text-slate-800">Resource:</span> {recommendation.finding.resource_type} / {recommendation.finding.resource_id}
                </p>
                <p>
                  <span className="font-semibold text-slate-800">Owner:</span> {owner}
                </p>
              </div>

              <div className="mt-4 rounded-2xl bg-white p-4">
                <p className="font-semibold text-slate-900">{recommendation.action}</p>
                <p className="mt-2 text-sm text-slate-600">{recommendation.rationale}</p>
                <ul className="mt-3 space-y-2 text-sm text-slate-700">
                  {recommendation.next_steps.map((step) => (
                    <li className="flex gap-2" key={step}>
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {STATUS_OPTIONS.map((option) => (
                  <button
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                      recommendation.status === option.value
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:text-blue-700"
                    }`}
                    key={option.value}
                    onClick={() => changeStatus(recommendation, option.value)}
                    type="button"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </Card>
  );
}
