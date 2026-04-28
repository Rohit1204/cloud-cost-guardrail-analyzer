# Deployment Guide

This guide describes local setup, AWS prerequisites, Terraform deployment, and local FastAPI testing.

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

## Local FastAPI Testing

```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn api:api --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Run guardrails:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H 'Content-Type: application/json' \
  -d '{"send_alerts": true, "alert_channels": ["gmail"], "gmail_recipient": "you@example.com"}'
```

## Destroy

```bash
cd infra
terraform destroy
```

Destroy removes the Lambda, EventBridge rule, IAM role, and log group. It does not delete any AWS resources the bot inspected.
