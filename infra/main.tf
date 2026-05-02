locals {
  project_root         = abspath("${path.module}/..")
  lambda_build_dir     = "${path.module}/.build/lambda"
  lambda_package_file  = "${path.module}/.build/cloud-cost-guardrail-bot.zip"
  frontend_bucket_name = var.frontend_bucket_name != "" ? var.frontend_bucket_name : "${var.project_name}-frontend-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

module "lambda" {
  source                          = "./modules/lambda"
  project_name                    = var.project_name
  project_root                    = local.project_root
  build_dir                       = local.lambda_build_dir
  package_file                    = local.lambda_package_file
  aws_region                      = var.aws_region
  lookback_days                   = var.lookback_days
  idle_cpu_threshold              = var.idle_cpu_threshold
  idle_db_connection_threshold    = var.idle_db_connection_threshold
  spend_spike_multiplier          = var.spend_spike_multiplier
  spend_spike_min_usd             = var.spend_spike_min_usd
  high_cost_service_threshold_usd = var.high_cost_service_threshold_usd
  alert_channels                  = var.alert_channels
  gmail_sender                    = var.gmail_sender
  gmail_recipient                 = var.gmail_recipient
  allowed_alert_recipients        = var.allowed_alert_recipients
  google_client_id                = var.google_client_id
  auth_allowed_emails             = var.auth_allowed_emails
  gmail_token_json                = var.gmail_token_json
  owner_tag_keys                  = var.owner_tag_keys
  environment_tag_keys            = var.environment_tag_keys
  owner_email_map                 = var.owner_email_map
  default_owner_email             = var.default_owner_email
  default_environment             = var.default_environment
  whatsapp_access_token           = var.whatsapp_access_token
  whatsapp_phone_number_id        = var.whatsapp_phone_number_id
  whatsapp_to                     = var.whatsapp_to
  whatsapp_api_version            = var.whatsapp_api_version
}

module "api_gateway" {
  source                          = "./modules/api_gateway"
  project_name                    = var.project_name
  lambda_function_name            = module.lambda.function_name
  lambda_invoke_arn               = module.lambda.invoke_arn
  frontend_allowed_origins        = var.frontend_allowed_origins
  alerts_run_throttle_rate_limit  = var.alerts_run_throttle_rate_limit
  alerts_run_throttle_burst_limit = var.alerts_run_throttle_burst_limit
}

module "schedule" {
  source               = "./modules/schedule"
  project_name         = var.project_name
  schedule_expression  = var.schedule_expression
  lambda_function_arn  = module.lambda.function_arn
  lambda_function_name = module.lambda.function_name
}

module "frontend_static" {
  source       = "./modules/frontend_static"
  project_name = var.project_name
  bucket_name  = local.frontend_bucket_name
  price_class  = var.frontend_cloudfront_price_class
}
