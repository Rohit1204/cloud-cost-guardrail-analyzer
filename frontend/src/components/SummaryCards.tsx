import { Activity, Bell, DollarSign, ShieldCheck } from "lucide-react";
import type { CostSummary, HealthResponse, RecommendationsResponse } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/format";
import { Card } from "./ui";

type Props = {
  costSummary: CostSummary | null | undefined;
  health: HealthResponse | null | undefined;
  recommendations: RecommendationsResponse | null | undefined;
};

export function SummaryCards({ costSummary, health, recommendations }: Props) {
  const currency = costSummary?.currency ?? "USD";
  const invoiceHint = costSummary?.month_to_date_invoice_hint;
  const invoiceCcy = costSummary?.month_to_date_invoice_hint_currency ?? currency;
  const showInvoiceHint = costSummary != null && invoiceHint != null;
  const cards: Array<{
    title: string;
    value: string;
    subdetail?: string;
    detail: string;
    icon: typeof DollarSign;
  }> = [
    {
      title: "Month To Date",
      value: formatMoney(costSummary?.month_to_date_unblended_cost, currency),
      subdetail: showInvoiceHint
        ? `Invoice-style hint (CE amortized): ${formatMoney(invoiceHint, invoiceCcy)}. Still not the AWS invoice (tax, credits, non-CE lines, lag).`
        : undefined,
      detail: costSummary
        ? `Cost Explorer usage basis (UTC). ${formatDate(costSummary.period.start)} to ${formatDate(costSummary.period.end)}. The Billing console total often looks higher: tax, AWS Support, some charges, and up to ~24h CE lag are not fully reflected here.`
        : "Waiting for Cost Explorer",
      icon: DollarSign,
    },
    {
      title: "Window Total",
      value: formatMoney(costSummary?.total_unblended_cost, currency),
      detail: `${costSummary?.months ?? 1} month window (same basis as MTD)`,
      icon: Activity,
    },
    {
      title: "Open Recommendations",
      value: String(recommendations?.recommendation_count ?? 0),
      detail: `${recommendations?.finding_count ?? 0} findings detected`,
      icon: ShieldCheck,
    },
    {
      title: "Notification Channels",
      value: String(health?.alert_channels?.length ?? 0),
      detail: health ? health.alert_channels.join(", ") || "No channels configured" : "Run backend check for readiness",
      icon: Bell,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-slate-500">{card.title}</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{card.value}</p>
              {card.subdetail ? <p className="mt-1 text-sm text-slate-600">{card.subdetail}</p> : null}
              <p className="mt-2 text-sm text-slate-500">{card.detail}</p>
            </div>
            <div className="rounded-2xl bg-blue-50 p-3 text-blue-600">
              <card.icon className="h-5 w-5" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
