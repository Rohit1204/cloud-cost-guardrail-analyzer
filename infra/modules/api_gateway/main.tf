resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["authorization", "content-type"]
    allow_methods = ["GET", "PATCH", "POST", "OPTIONS"]
    allow_origins = var.frontend_allowed_origins
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "docs" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /docs"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "openapi" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /openapi.json"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "costs_summary" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /costs/summary"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "recommendations" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /recommendations"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "recommendations_status" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "PATCH /recommendations/status"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "alerts_run" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /alerts/run"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "run" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /run"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  route_settings {
    route_key              = aws_apigatewayv2_route.alerts_run.route_key
    throttling_burst_limit = var.alerts_run_throttle_burst_limit
    throttling_rate_limit  = var.alerts_run_throttle_rate_limit
  }
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
