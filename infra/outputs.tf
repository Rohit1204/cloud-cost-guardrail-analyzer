output "lambda_function_name" {
  description = "Name of the deployed Lambda function."
  value       = module.lambda.function_name
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge schedule rule."
  value       = module.schedule.rule_name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda execution logs."
  value       = module.lambda.cloudwatch_log_group_name
}

output "api_gateway_endpoint" {
  description = "HTTP API endpoint for frontend and manual API access."
  value       = module.api_gateway.api_endpoint
}

output "frontend_bucket_name" {
  description = "S3 bucket that stores the static Next.js export."
  value       = module.frontend_static.bucket_name
}

output "frontend_cloudfront_domain_name" {
  description = "CloudFront domain name for the static frontend."
  value       = module.frontend_static.cloudfront_domain_name
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidations."
  value       = module.frontend_static.cloudfront_distribution_id
}

output "frontend_cloudfront_url" {
  description = "HTTPS URL for the static frontend."
  value       = module.frontend_static.cloudfront_url
}

output "frontend_deploy_command" {
  description = "Command to upload the built frontend/out directory to S3."
  value       = "aws s3 sync ../frontend/out/ s3://${module.frontend_static.bucket_name}/ --delete"
}

output "billing_console_role_arn" {
  description = "IAM role used for federated Billing console URLs (STS + console federation)."
  value       = module.lambda.billing_console_role_arn
}
