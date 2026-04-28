export type DetectorError = {
  detector: string;
  error_type: string;
  message: string;
};

export type HealthResponse = {
  status: string;
  target_region: string;
  alert_channels: string[];
  gmail_token_configured: boolean;
  gmail_recipient_configured: boolean;
  whatsapp_configured: boolean;
};

export type CostPoint = {
  start: string;
  end: string;
  amount: number;
  currency: string;
};

export type ServiceCost = {
  service: string;
  amount: number;
  currency: string;
};

export type CostSummary = {
  months: number;
  period: { start: string; end: string };
  total_unblended_cost: number;
  month_to_date_unblended_cost: number;
  currency: string;
  monthly_costs: CostPoint[];
  top_services: ServiceCost[];
};

export type CostSummaryResponse = {
  cost_summary: CostSummary | null;
  errors: DetectorError[];
};

export type Finding = {
  category: string;
  resource_id: string;
  resource_type: string;
  region: string;
  title: string;
  description: string;
  metric_name: string;
  metric_value: number;
  threshold: number;
  estimated_monthly_savings?: number | null;
  metadata: Record<string, unknown>;
};

export type Recommendation = {
  finding: Finding;
  priority: "critical" | "warning" | "info" | string;
  action: string;
  rationale: string;
  next_steps: string[];
};

export type RecommendationsResponse = {
  type: "recommendations";
  cost_summary: CostSummary | null;
  finding_count: number;
  recommendation_count: number;
  findings: Finding[];
  recommendations: Recommendation[];
  errors: DetectorError[];
};

export type NotificationResult = {
  channel: string;
  delivered: boolean;
  detail: string;
};

export type AlertRunRequest = {
  cost_months: number;
  alert_channels: string[];
  gmail_recipient?: string;
};

export type AlertRunResponse = {
  type: "alert_run";
  alert_run: {
    delivery_status: string;
    requested_channels: string[];
    notification_count: number;
    recommendations_sent_count: number;
  };
  cost_summary: CostSummary | null;
  finding_count: number;
  recommendation_count: number;
  notifications: NotificationResult[];
  errors: DetectorError[];
};
