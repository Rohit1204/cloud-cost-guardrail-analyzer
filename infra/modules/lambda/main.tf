locals {
  source_files = fileset("${var.project_root}/src", "**/*.py")
  source_hash  = sha256(join("", [for file in local.source_files : filesha256("${var.project_root}/src/${file}")]))
}

resource "null_resource" "lambda_build" {
  triggers = {
    requirements = filesha256("${var.project_root}/requirements.txt")
    source       = local.source_hash
    packaging    = "manylinux2014-x86_64-python311-v1"
  }

  provisioner "local-exec" {
    command = <<-EOT
rm -rf "${var.build_dir}"
mkdir -p "${var.build_dir}"
python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  --upgrade \
  -r "${var.project_root}/requirements.txt" \
  -t "${var.build_dir}"
cp -R "${var.project_root}/src/"* "${var.build_dir}/"
EOT
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = var.build_dir
  output_path = var.package_file

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

  statement {
    sid = "RecommendationStatus"
    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem"
    ]
    resources = [aws_dynamodb_table.recommendation_status.arn]
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

resource "aws_dynamodb_table" "recommendation_status" {
  name         = "${var.project_name}-recommendation-status"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "recommendation_id"

  attribute {
    name = "recommendation_id"
    type = "S"
  }
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
      ALLOWED_ALERT_RECIPIENTS        = var.allowed_alert_recipients
      GOOGLE_CLIENT_ID                = var.google_client_id
      AUTH_ALLOWED_EMAILS             = var.auth_allowed_emails != "" ? var.auth_allowed_emails : var.allowed_alert_recipients
      GMAIL_TOKEN_JSON                = var.gmail_token_json
      OWNER_TAG_KEYS                  = var.owner_tag_keys
      ENVIRONMENT_TAG_KEYS            = var.environment_tag_keys
      OWNER_EMAIL_MAP                 = var.owner_email_map
      DEFAULT_OWNER_EMAIL             = var.default_owner_email
      DEFAULT_ENVIRONMENT             = var.default_environment
      RECOMMENDATION_STATUS_TABLE     = aws_dynamodb_table.recommendation_status.name
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
