import type { AlertRunResponse, CostSummaryResponse, HealthResponse, RecommendationsResponse } from "@/lib/types";

export const healthFixture: HealthResponse = {
  status: "ok",
  target_region: "ap-south-1",
  alert_channels: ["gmail"],
  gmail_token_configured: true,
  gmail_recipient_configured: true,
  whatsapp_configured: false,
  billing_console_federation_enabled: true,
};

export const costSummaryFixture: CostSummaryResponse = {
  cost_summary: {
    months: 1,
    period: { start: "2026-04-01", end: "2026-04-29" },
    total_unblended_cost: 12.34,
    month_to_date_unblended_cost: 12.34,
    currency: "USD",
    monthly_costs: [{ start: "2026-04-01", end: "2026-04-29", amount: 12.34, currency: "USD" }],
    top_services: [
      { service: "Amazon Elastic Compute Cloud - Compute", amount: 8.12, currency: "USD" },
      { service: "Amazon Simple Storage Service", amount: 4.22, currency: "USD" },
    ],
  },
  errors: [],
};

export const recommendationsFixture: RecommendationsResponse = {
  type: "recommendations",
  cost_summary: costSummaryFixture.cost_summary,
  finding_count: 2,
  recommendation_count: 2,
  findings: [],
  recommendations: [
    {
      recommendation_id: "rec-warning-ebs",
      status: "new",
      priority: "warning",
      action: "Snapshot and delete the unattached volume.",
      rationale: "Detached EBS volumes continue billing while unused.",
      next_steps: ["Create a final snapshot.", "Delete after validation."],
      finding: {
        category: "unattached_ebs",
        resource_id: "vol-001",
        resource_type: "ebs-volume",
        region: "ap-south-1",
        title: "Unattached EBS volume: vol-001",
        description: "Volume has been detached for 10 days.",
        metric_name: "age_days",
        metric_value: 10,
        threshold: 0,
        estimated_monthly_savings: 8,
        metadata: { owner: "platform", environment: "dev" },
      },
    },
    {
      recommendation_id: "rec-critical-ec2",
      status: "acknowledged",
      priority: "critical",
      action: "Stop or rightsize the idle EC2 instance after owner validation.",
      rationale: "Idle compute is contributing unnecessary spend.",
      next_steps: ["Confirm workload ownership.", "Apply a stop schedule or rightsize the instance."],
      finding: {
        category: "idle_ec2",
        resource_id: "i-001",
        resource_type: "ec2-instance",
        region: "ap-south-1",
        title: "Idle EC2 instance: i-001",
        description: "Instance CPU has remained below threshold.",
        metric_name: "CPUUtilization",
        metric_value: 1,
        threshold: 5,
        estimated_monthly_savings: 42,
        metadata: { owner: "payments", environment: "prod" },
      },
    },
  ],
  errors: [],
};

export const alertRunFixture: AlertRunResponse = {
  type: "alert_run",
  alert_run: {
    delivery_status: "delivered",
    requested_channels: ["gmail"],
    notification_count: 1,
    recommendations_sent_count: 1,
  },
  cost_summary: costSummaryFixture.cost_summary,
  finding_count: 1,
  recommendation_count: 1,
  notifications: [{ channel: "gmail", delivered: true, detail: "sent" }],
  errors: [],
};
