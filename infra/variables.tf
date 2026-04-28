variable "aws_region" {
  description = "AWS region for regional resource checks and Lambda deployment."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix for deployed resources."
  type        = string
  default     = "cloud-cost-guardrail-bot"
}

variable "frontend_allowed_origins" {
  description = "Allowed browser origins for API Gateway CORS."
  type        = list(string)
  default     = ["http://localhost:3000", "http://127.0.0.1:3000"]
}

variable "frontend_bucket_name" {
  description = "Optional S3 bucket name for the static Next.js export. Leave empty to derive one from project_name."
  type        = string
  default     = ""
}

variable "frontend_cloudfront_price_class" {
  description = "CloudFront price class for the static frontend distribution."
  type        = string
  default     = "PriceClass_100"
}

variable "alerts_run_throttle_rate_limit" {
  description = "Steady-state requests per second allowed for POST /alerts/run."
  type        = number
  default     = 1
}

variable "alerts_run_throttle_burst_limit" {
  description = "Burst request limit for POST /alerts/run."
  type        = number
  default     = 2
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for cost guardrail checks."
  type        = string
  default     = "rate(1 day)"
}

variable "lookback_days" {
  description = "Number of days to inspect for resource metrics and cost baseline."
  type        = number
  default     = 7
}

variable "idle_cpu_threshold" {
  description = "Average CPU percentage below which compute resources are considered idle."
  type        = number
  default     = 5
}

variable "idle_db_connection_threshold" {
  description = "Average RDS connection count below which a database is considered idle."
  type        = number
  default     = 1
}

variable "spend_spike_multiplier" {
  description = "Latest daily spend must exceed baseline by this multiplier to alert."
  type        = number
  default     = 1.5
}

variable "spend_spike_min_usd" {
  description = "Minimum latest daily spend required before spike alerts fire."
  type        = number
  default     = 25
}

variable "high_cost_service_threshold_usd" {
  description = "Lookback-window service spend threshold for savings review alerts."
  type        = number
  default     = 100
}

variable "alert_channels" {
  description = "Comma-separated alert channels. Supported values: gmail,whatsapp."
  type        = string
  default     = "gmail,whatsapp"
}

variable "gmail_sender" {
  description = "Gmail user id. Use 'me' for the OAuth-authenticated account."
  type        = string
  default     = "me"
}

variable "gmail_recipient" {
  description = "Email address that receives alerts."
  type        = string
  default     = ""
}

variable "allowed_alert_recipients" {
  description = "Comma-separated allowlist of Gmail recipient overrides accepted by the alert API."
  type        = string
  default     = ""
}

variable "google_client_id" {
  description = "Google OAuth web client ID used to verify frontend Google sign-in ID tokens. Leave empty to disable API auth."
  type        = string
  default     = ""
}

variable "auth_allowed_emails" {
  description = "Comma-separated Google account emails allowed to use the dashboard API."
  type        = string
  default     = ""
}

variable "gmail_token_json" {
  description = "Gmail OAuth authorized-user token JSON. Sensitive and stored in Terraform state if set here."
  type        = string
  default     = ""
  sensitive   = true
}

variable "owner_tag_keys" {
  description = "Comma-separated AWS tag keys used to identify the owner or team for alert routing."
  type        = string
  default     = "OwnerEmail,owner_email,Owner,owner,Team,team"
}

variable "environment_tag_keys" {
  description = "Comma-separated AWS tag keys used to identify environment for alert context and routing."
  type        = string
  default     = "Environment,environment,Env,env,Stage,stage"
}

variable "owner_email_map" {
  description = "JSON map from owner, environment, or environment:owner to alert email address."
  type        = string
  default     = "{}"
}

variable "default_owner_email" {
  description = "Fallback email route when no owner tag or owner map entry is found."
  type        = string
  default     = ""
}

variable "default_environment" {
  description = "Fallback environment label for untagged account-level findings."
  type        = string
  default     = ""
}

variable "whatsapp_access_token" {
  description = "Meta WhatsApp Cloud API access token. Sensitive and stored in Terraform state if set here."
  type        = string
  default     = ""
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "Meta WhatsApp Cloud API phone number id."
  type        = string
  default     = ""
}

variable "whatsapp_to" {
  description = "Recipient phone number in international format without '+'."
  type        = string
  default     = ""
}

variable "whatsapp_api_version" {
  description = "Meta Graph API version."
  type        = string
  default     = "v19.0"
}
