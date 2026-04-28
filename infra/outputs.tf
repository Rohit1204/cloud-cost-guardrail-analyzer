output "lambda_function_name" {
  description = "Name of the deployed Lambda function."
  value       = aws_lambda_function.guardrail.function_name
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge schedule rule."
  value       = aws_cloudwatch_event_rule.schedule.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda execution logs."
  value       = aws_cloudwatch_log_group.lambda.name
}

output "api_gateway_endpoint" {
  description = "HTTP API endpoint for frontend and manual API access."
  value       = aws_apigatewayv2_api.http.api_endpoint
}
