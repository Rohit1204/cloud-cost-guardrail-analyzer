import type { Recommendation } from "@/lib/types";
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

export function RecommendationsList({ recommendations }: { recommendations: Recommendation[] }) {
  if (recommendations.length === 0) {
    return <EmptyBlock title="No recommendations" detail="No actionable findings crossed your configured thresholds." />;
  }

  return (
    <Card>
      <SectionHeader eyebrow="Actions" title="Recommended guardrails" />
      <div className="space-y-4">
        {recommendations.map((recommendation) => {
          const owner = metadataValue(recommendation.finding.metadata, "owner") ?? "Unassigned";
          const environment = metadataValue(recommendation.finding.metadata, "environment") ?? "Unknown environment";
          const savings = recommendation.finding.estimated_monthly_savings;

          return (
            <article className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4" key={`${recommendation.finding.category}-${recommendation.finding.resource_id}`}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone={priorityTone(recommendation.priority)}>{sentenceCase(recommendation.priority)}</Badge>
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

              <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-3">
                <p>
                  <span className="font-semibold text-slate-800">Resource:</span> {recommendation.finding.resource_type} / {recommendation.finding.resource_id}
                </p>
                <p>
                  <span className="font-semibold text-slate-800">Region:</span> {recommendation.finding.region}
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
            </article>
          );
        })}
      </div>
    </Card>
  );
}
