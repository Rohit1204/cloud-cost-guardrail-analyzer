export type DetectorError = {
  detector: string;
  error_type: string;
  message: string;
};

export type HealthResponse = {
  status: string;
  auth_enabled?: boolean;
  authenticated_user?: string | null;
  target_region: string;
  alert_channels: string[];
  gmail_token_configured: boolean;
  gmail_recipient_configured: boolean;
  whatsapp_configured: boolean;
  billing_console_federation_enabled?: boolean;
};

export type BillingConsoleUrlResponse = {
  url: string;
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

/** Closed billing month totals from AWS Invoice Summary API (ListInvoiceSummaries). */
export type InvoiceBillingPeriodSummary = {
  billing_period: { year: number; month: number };
  invoice_ids: string[];
  /** Primary total for display: payment currency when AWS sends it, else base invoice currency. */
  total_amount: number | null;
  total_before_tax: number | null;
  currency: string | null;
  display_basis?: "payment_currency" | "base_currency";
  base_total_amount?: number | null;
  base_total_before_tax?: number | null;
  base_currency?: string | null;
  payment_total_amount?: number | null;
  payment_total_before_tax?: number | null;
  payment_currency?: string | null;
  tax_currency_total_amount?: number | null;
  tax_currency?: string | null;
  issued_date: number | null;
};

export type InvoiceBilling = {
  available: boolean;
  skipped?: boolean;
  account_id?: string;
  source?: string;
  error?: { error_type: string; message: string };
  current_period?: InvoiceBillingPeriodSummary | null;
  prior_period?: InvoiceBillingPeriodSummary | null;
};

export type CostSummary = {
  months: number;
  period: { start: string; end: string };
  total_unblended_cost: number;
  month_to_date_unblended_cost: number;
  currency: string;
  monthly_costs: CostPoint[];
  top_services: ServiceCost[];
  /** Which CE metric was used first (Unblended → Net → Blended → amortized fallbacks). */
  usage_cost_basis?: string;
  /** Daily CE sum using NetAmortizedCost then AmortizedCost when present; not the AWS invoice. */
  month_to_date_invoice_hint?: number | null;
  month_to_date_invoice_hint_currency?: string | null;
  invoice_hint_basis?: string | null;
  invoice_billing?: InvoiceBilling;
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

export type RecommendationStatus = "new" | "acknowledged" | "in_progress" | "resolved";

export type Recommendation = {
  recommendation_id: string;
  status: RecommendationStatus;
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

export type RecommendationStatusUpdateRequest = {
  recommendation_id: string;
  status: RecommendationStatus;
};

export type RecommendationStatusUpdateResponse = RecommendationStatusUpdateRequest & {
  updated_at: string;
};
