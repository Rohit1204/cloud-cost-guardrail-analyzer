output "api_endpoint" {
  description = "HTTP API endpoint URL."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "execution_arn" {
  description = "API Gateway execution ARN."
  value       = aws_apigatewayv2_api.http.execution_arn
}
