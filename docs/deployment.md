# Deployment Guide

This guide describes local setup, AWS prerequisites, Terraform deployment, API Gateway access, and local FastAPI testing.

## AWS Prerequisites

- AWS CLI installed and authenticated.
- Target account has Cost Explorer enabled.
- Caller can create IAM roles, Lambda functions, EventBridge rules, and CloudWatch log groups.
- Caller can read Cost Explorer and resource inventory APIs.

Verify credentials:

```bash
aws sts get-caller-identity
```

If using a named profile:

```bash
AWS_PROFILE=cloud-cost-bot aws sts get-caller-identity
```

## Cost Explorer

Cost Explorer must be enabled in the payer account. New accounts or newly enabled Cost Explorer setups may return `DataUnavailableException` for several hours, sometimes up to 24 hours.

Test manually:

```bash
aws ce get-cost-and-usage \
  --region us-east-1 \
  --time-period Start=2026-04-01,End=2026-04-28 \
  --granularity MONTHLY \
  --metrics UnblendedCost
```

Cost Explorer uses a global endpoint and is commonly called through `us-east-1` even when the resources are in `ap-south-1`.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Generate Gmail token:

```bash
python scripts/generate_gmail_token.py --print-terraform-var
```

## Terraform Variables

Create `infra/terraform.tfvars`. Do not commit it.

```hcl
aws_region      = "ap-south-1"
alert_channels  = "gmail"
gmail_sender    = "me"
gmail_recipient = "you@example.com"
gmail_token_json = <<EOT
{
  "token": "...",
  "refresh_token": "...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "...",
  "client_secret": "...",
  "scopes": ["https://www.googleapis.com/auth/gmail.send"]
}
EOT
owner_tag_keys       = "OwnerEmail,Owner,Team"
environment_tag_keys = "Environment,Stage"
owner_email_map = <<EOT
{
  "platform": "platform@example.com",
  "prod:payments": "payments-oncall@example.com"
}
EOT
default_owner_email = "cloud-cost-owner@example.com"
default_environment = "dev"
```

Add WhatsApp variables only when ready:

```hcl
alert_channels             = "gmail,whatsapp"
whatsapp_access_token      = "..."
whatsapp_phone_number_id   = "..."
whatsapp_to                = "919999999999"
```

## Deploy

```bash
cd infra
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Using a named AWS profile:

```bash
AWS_PROFILE=cloud-cost-bot terraform plan
AWS_PROFILE=cloud-cost-bot terraform apply
```

## Invoke Deployed Lambda

```bash
aws lambda invoke \
  --region ap-south-1 \
  --function-name cloud-cost-guardrail-bot \
  response.json
```

## API Gateway For Frontend

Terraform creates an API Gateway HTTP API in front of the Lambda.

Get the endpoint:

```bash
terraform output api_gateway_endpoint
```

Health check:

```bash
curl "$(terraform output -raw api_gateway_endpoint)/health"
```

Cost summary for charts:

```bash
curl "$(terraform output -raw api_gateway_endpoint)/costs/summary?months=6"
```

Read-only recommendations:

```bash
curl "$(terraform output -raw api_gateway_endpoint)/recommendations?months=1"
```

Swagger docs:

```bash
open "$(terraform output -raw api_gateway_endpoint)/docs"
curl "$(terraform output -raw api_gateway_endpoint)/openapi.json"
```

Run guardrails and send alerts through API Gateway:

```bash
curl -X POST "$(terraform output -raw api_gateway_endpoint)/alerts/run" \
  -H 'Content-Type: application/json' \
  -d '{"cost_months": 6, "alert_channels": ["gmail"], "gmail_recipient": "you@example.com"}'
```

The `/costs/summary` and `/recommendations` responses include `cost_summary.month_to_date_unblended_cost`, `cost_summary.total_unblended_cost`, `cost_summary.monthly_costs`, and `cost_summary.top_services` when Cost Explorer data is available. `/alerts/run` returns the same cost summary plus notification delivery status and summary counts. Set `months` or `cost_months` to a value from 1 to 12 depending on the frontend view.

For a browser frontend, add authentication and authorization before exposing `/alerts/run` publicly. Good production options are Cognito authorizers, JWT authorizers, or a private API behind an authenticated backend.

API Gateway CORS is enabled for `frontend_allowed_origins`. For local Next.js development the defaults allow `http://localhost:3000` and `http://127.0.0.1:3000`. Add your deployed frontend origin before applying Terraform:

```hcl
frontend_allowed_origins = [
  "http://localhost:3000",
  "https://your-frontend.example.com"
]
```

## Next.js Frontend

Run the dashboard locally:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to the local FastAPI URL or the deployed API Gateway endpoint:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_BASE_URL=https://your-api-id.execute-api.ap-south-1.amazonaws.com
```

The frontend is configured as a static export, so `npm run build` writes deployable static files to `frontend/out/`.

Build with the deployed API Gateway endpoint:

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL="https://xyqayo8x14.execute-api.ap-south-1.amazonaws.com" npm run build
```

Deploy the generated files to S3:

```bash
aws s3 sync out/ s3://your-frontend-bucket --delete
```

Recommended production hosting:

```text
Browser -> CloudFront -> S3 static frontend
Browser -> API Gateway -> Lambda backend
```

After CloudFront is created, add its domain to `frontend_allowed_origins` and apply Terraform again so API Gateway CORS allows the hosted frontend.

## Local FastAPI Testing

```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn api:api --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Fetch costs and recommendations:

```bash
curl "http://127.0.0.1:8000/costs/summary?months=6"
curl "http://127.0.0.1:8000/recommendations?months=1"
```

Run guardrails and send alerts:

```bash
curl -X POST http://127.0.0.1:8000/alerts/run \
  -H 'Content-Type: application/json' \
  -d '{"cost_months": 12, "alert_channels": ["gmail"], "gmail_recipient": "you@example.com"}'
```

## Destroy

```bash
cd infra
terraform destroy
```

Destroy removes the Lambda, EventBridge rule, IAM role, and log group. It does not delete any AWS resources the bot inspected.
