locals {
  build_dir    = "${path.module}/.build/lambda"
  package_file = "${path.module}/.build/cloud-cost-guardrail-bot.zip"
  source_files = fileset("${path.module}/../src", "**/*.py")
  source_hash  = sha256(join("", [for file in local.source_files : filesha256("${path.module}/../src/${file}")]))
}

resource "null_resource" "lambda_build" {
  triggers = {
    requirements = filesha256("${path.module}/../requirements.txt")
    source       = local.source_hash
    packaging    = "manylinux2014-x86_64-python311-v1"
  }

  provisioner "local-exec" {
    command = <<EOT
rm -rf "${path.module}/.build"
mkdir -p "${local.build_dir}"
python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  --upgrade \
  -r "${path.module}/../requirements.txt" \
  -t "${local.build_dir}"
cp -R "${path.module}/../src/"* "${local.build_dir}/"
EOT
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.build_dir
  output_path = local.package_file

  depends_on = [null_resource.lambda_build]
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid = "ReadCostExplorer"
    actions = [
      "ce:GetCostAndUsage",
      "ce:GetCostForecast",
      "ce:GetDimensionValues",
      "ce:GetRightsizingRecommendation",
      "ce:GetSavingsPlansPurchaseRecommendation"
    ]
    resources = ["*"]
  }

  statement {
    sid = "ReadResourceInventory"
    actions = [
      "ec2:DescribeInstances",
      "ec2:DescribeVolumes",
      "rds:DescribeDBInstances",
      "rds:ListTagsForResource",
      "cloudwatch:GetMetricStatistics"
    ]
    resources = ["*"]
  }

  statement {
    sid = "WriteLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${var.project_name}-lambda-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 30
}

resource "aws_lambda_function" "guardrail" {
  function_name    = var.project_name
  role             = aws_iam_role.lambda.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.11"
  architectures    = ["x86_64"]
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      TARGET_AWS_REGION               = var.aws_region
      LOOKBACK_DAYS                   = tostring(var.lookback_days)
      IDLE_CPU_THRESHOLD              = tostring(var.idle_cpu_threshold)
      IDLE_DB_CONNECTION_THRESHOLD    = tostring(var.idle_db_connection_threshold)
      SPEND_SPIKE_MULTIPLIER          = tostring(var.spend_spike_multiplier)
      SPEND_SPIKE_MIN_USD             = tostring(var.spend_spike_min_usd)
      HIGH_COST_SERVICE_THRESHOLD_USD = tostring(var.high_cost_service_threshold_usd)
      ALERT_CHANNELS                  = var.alert_channels
      GMAIL_SENDER                    = var.gmail_sender
      GMAIL_RECIPIENT                 = var.gmail_recipient
      GMAIL_TOKEN_JSON                = var.gmail_token_json
      OWNER_TAG_KEYS                  = var.owner_tag_keys
      ENVIRONMENT_TAG_KEYS            = var.environment_tag_keys
      OWNER_EMAIL_MAP                 = var.owner_email_map
      DEFAULT_OWNER_EMAIL             = var.default_owner_email
      DEFAULT_ENVIRONMENT             = var.default_environment
      WHATSAPP_ACCESS_TOKEN           = var.whatsapp_access_token
      WHATSAPP_PHONE_NUMBER_ID        = var.whatsapp_phone_number_id
      WHATSAPP_TO                     = var.whatsapp_to
      WHATSAPP_API_VERSION            = var.whatsapp_api_version
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda,
    aws_cloudwatch_log_group.lambda
  ]
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.project_name}-schedule"
  description         = "Runs the Cloud Cost Guardrail Bot on a schedule."
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "${var.project_name}-lambda"
  arn       = aws_lambda_function.guardrail.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guardrail.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.guardrail.invoke_arn
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
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guardrail.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
