variable "project_name" {
  description = "Resource name prefix."
  type        = string
}

variable "project_root" {
  description = "Absolute path to the repository root for packaging Lambda."
  type        = string
}

variable "build_dir" {
  description = "Directory used for pip install and Lambda package assembly."
  type        = string
}

variable "package_file" {
  description = "Zip artifact path for Lambda deployment."
  type        = string
}

variable "aws_region" {
  description = "Target AWS region passed into Lambda as TARGET_AWS_REGION."
  type        = string
}

variable "lookback_days" {
  type = number
}

variable "idle_cpu_threshold" {
  type = number
}

variable "idle_db_connection_threshold" {
  type = number
}

variable "spend_spike_multiplier" {
  type = number
}

variable "spend_spike_min_usd" {
  type = number
}

variable "high_cost_service_threshold_usd" {
  type = number
}

variable "alert_channels" {
  type = string
}

variable "gmail_sender" {
  type = string
}

variable "gmail_recipient" {
  type = string
}

variable "allowed_alert_recipients" {
  type = string
}

variable "google_client_id" {
  type = string
}

variable "auth_allowed_emails" {
  type = string
}

variable "gmail_token_json" {
  type      = string
  sensitive = true
}

variable "owner_tag_keys" {
  type = string
}

variable "environment_tag_keys" {
  type = string
}

variable "owner_email_map" {
  type = string
}

variable "default_owner_email" {
  type = string
}

variable "default_environment" {
  type = string
}

variable "whatsapp_access_token" {
  type      = string
  sensitive = true
}

variable "whatsapp_phone_number_id" {
  type = string
}

variable "whatsapp_to" {
  type = string
}

variable "whatsapp_api_version" {
  type = string
}
