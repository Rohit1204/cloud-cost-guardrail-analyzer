output "function_name" {
  description = "Deployed Lambda function name."
  value       = aws_lambda_function.guardrail.function_name
}

output "function_arn" {
  description = "Deployed Lambda function ARN."
  value       = aws_lambda_function.guardrail.arn
}

output "invoke_arn" {
  description = "Lambda invoke ARN for API Gateway integration."
  value       = aws_lambda_function.guardrail.invoke_arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group for Lambda execution logs."
  value       = aws_cloudwatch_log_group.lambda.name
}

output "recommendation_status_table_name" {
  description = "DynamoDB table storing recommendation workflow status."
  value       = aws_dynamodb_table.recommendation_status.name
}

output "billing_console_role_arn" {
  description = "IAM role assumed for federated AWS Billing console sign-in from GET /billing/console-url."
  value       = aws_iam_role.billing_console.arn
}
