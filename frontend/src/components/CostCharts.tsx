"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CostSummary } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { Card, EmptyBlock, SectionHeader } from "./ui";

type Props = {
  summary: CostSummary | null | undefined;
};

export function CostCharts({ summary }: Props) {
  if (!summary) {
    return <EmptyBlock title="No cost data yet" detail="Cost Explorer may still be ingesting data for this account." />;
  }

  const monthlyData = summary.monthly_costs.map((point) => ({
    month: new Intl.DateTimeFormat("en", { month: "short", timeZone: "UTC" }).format(
      /^\d{4}-\d{2}-\d{2}$/.test(String(point.start ?? "").trim())
        ? new Date(`${String(point.start).trim()}T00:00:00.000Z`)
        : new Date(point.start),
    ),
    amount: point.amount,
  }));

  const serviceData = summary.top_services.slice(0, 6).map((service) => ({
    service: service.service.replace("Amazon ", "").replace("AWS ", ""),
    amount: service.amount,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <SectionHeader eyebrow="Trend" title="Monthly cost movement" />
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={monthlyData} margin={{ left: 4, right: 20, top: 12, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} tickFormatter={(value) => formatMoney(Number(value), summary.currency)} />
              <Tooltip formatter={(value) => formatMoney(Number(value), summary.currency)} />
              <Line type="monotone" dataKey="amount" stroke="#2563eb" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <SectionHeader eyebrow="Drivers" title="Top services" />
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={serviceData} layout="vertical" margin={{ left: 12, right: 20, top: 12, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" stroke="#64748b" fontSize={12} tickFormatter={(value) => formatMoney(Number(value), summary.currency)} />
              <YAxis type="category" dataKey="service" width={110} stroke="#64748b" fontSize={12} />
              <Tooltip formatter={(value) => formatMoney(Number(value), summary.currency)} />
              <Bar dataKey="amount" fill="#0ea5e9" radius={[0, 10, 10, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
