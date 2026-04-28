# Configuration Reference

Configuration is supplied through Terraform variables for deployed Lambda and environment variables or local files for local runs.

## Runtime Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `TARGET_AWS_REGION` | `ap-south-1` | Region used for EC2, EBS, RDS, and CloudWatch checks. |
| `LOOKBACK_DAYS` | `7` | Number of days used for metrics and cost baselines. |
| `IDLE_CPU_THRESHOLD` | `5` | Average CPU percentage below which compute is considered idle. |
| `IDLE_DB_CONNECTION_THRESHOLD` | `1` | Average RDS connection count below which a database is considered idle. |
| `SPEND_SPIKE_MULTIPLIER` | `1.5` | Latest daily spend must exceed baseline by this multiplier. |
| `SPEND_SPIKE_MIN_USD` | `25` | Minimum latest daily spend before spike alerts fire. |
| `HIGH_COST_SERVICE_THRESHOLD_USD` | `100` | Service spend threshold for savings review. |
| `ALERT_CHANNELS` | `gmail,whatsapp` | Comma-separated notification channels. |
| `GMAIL_SENDER` | `me` in Terraform | Gmail user ID. `me` means the OAuth-authenticated user. |
| `GMAIL_RECIPIENT` | empty | Email alert recipient. |
| `ALLOWED_ALERT_RECIPIENTS` | `GMAIL_RECIPIENT` locally, empty in Terraform unless set | Comma-separated allowlist for Gmail recipient overrides accepted by `/alerts/run`. |
| `GMAIL_TOKEN_JSON` | empty | Authorized-user Gmail token JSON. |
| `GMAIL_TOKEN_FILE` | `gmail_token.json` | Local token file used when `GMAIL_TOKEN_JSON` is absent. |
| `OWNER_TAG_KEYS` | `OwnerEmail,owner_email,Owner,owner,Team,team` | Tag keys used to find owner or team routing values. |
| `ENVIRONMENT_TAG_KEYS` | `Environment,environment,Env,env,Stage,stage` | Tag keys used to find environment context. |
| `OWNER_EMAIL_MAP` | `{}` | JSON map from owner, environment, or `environment:owner` to email address. |
| `DEFAULT_OWNER_EMAIL` | empty | Fallback email route when no owner route is resolved. |
| `DEFAULT_ENVIRONMENT` | empty | Fallback environment label for untagged account-level findings. |
| `WHATSAPP_ACCESS_TOKEN` | empty | Meta WhatsApp Cloud API access token. |
| `WHATSAPP_PHONE_NUMBER_ID` | empty | Meta phone number ID. |
| `WHATSAPP_TO` | empty | Recipient phone number in international format without `+`. |
| `WHATSAPP_API_VERSION` | `v19.0` | Meta Graph API version. |

## Terraform Variables

| Variable | Default | Description |
| --- | --- | --- |
| `aws_region` | `ap-south-1` | AWS region for Lambda and regional checks. |
| `project_name` | `cloud-cost-guardrail-bot` | Resource name prefix. |
| `frontend_allowed_origins` | `["http://localhost:3000", "http://127.0.0.1:3000"]` | Browser origins allowed by API Gateway CORS. |
| `schedule_expression` | `rate(1 day)` | EventBridge schedule. |
| `lookback_days` | `7` | Metric and cost lookback period. |
| `idle_cpu_threshold` | `5` | Idle CPU threshold. |
| `idle_db_connection_threshold` | `1` | Idle RDS connection threshold. |
| `spend_spike_multiplier` | `1.5` | Spend spike multiplier. |
| `spend_spike_min_usd` | `25` | Minimum spend for spike detection. |
| `high_cost_service_threshold_usd` | `100` | High-cost service review threshold. |
| `alert_channels` | `gmail,whatsapp` | Enabled notification channels. |
| `gmail_sender` | `me` | Gmail sender user ID. |
| `gmail_recipient` | empty | Gmail recipient address. |
| `allowed_alert_recipients` | empty | Comma-separated allowlist of Gmail recipient overrides accepted by the alert API. |
| `gmail_token_json` | empty | Gmail OAuth token JSON. Sensitive. |
| `owner_tag_keys` | `OwnerEmail,owner_email,Owner,owner,Team,team` | Comma-separated tag keys used for owner routing. |
| `environment_tag_keys` | `Environment,environment,Env,env,Stage,stage` | Comma-separated tag keys used for environment context. |
| `owner_email_map` | `{}` | JSON owner-to-email routing map. |
| `default_owner_email` | empty | Fallback owner route. |
| `default_environment` | empty | Fallback environment label. |
| `whatsapp_access_token` | empty | WhatsApp access token. Sensitive. |
| `whatsapp_phone_number_id` | empty | WhatsApp phone number ID. |
| `whatsapp_to` | empty | WhatsApp recipient number. |
| `whatsapp_api_version` | `v19.0` | Meta Graph API version. |

## Recommended Defaults

Development:

```hcl
alert_channels = "gmail"
lookback_days  = 7
```

Production:

```hcl
schedule_expression                = "cron(30 3 * * ? *)"
lookback_days                      = 14
spend_spike_multiplier             = 1.5
spend_spike_min_usd                = 25
high_cost_service_threshold_usd    = 100
```

Tune thresholds based on account size and expected daily spend.

`cost_summary` is not threshold-based. It always attempts to return unblended cost and top services from Cost Explorer. Use the `/costs/summary?months=6` query parameter for read-only cost views, or `cost_months` in `/alerts/run` requests. Supported windows are 1 to 12 months.

## Frontend Environment

The Next.js app reads its backend URL from `NEXT_PUBLIC_API_BASE_URL`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ALLOWED_ALERT_EMAILS=you@example.com,cloud-cost-owner@example.com
```

Use the local FastAPI URL during development or the Terraform `api_gateway_endpoint` output after deployment:

```bash
NEXT_PUBLIC_API_BASE_URL=https://xyqayo8x14.execute-api.ap-south-1.amazonaws.com
NEXT_PUBLIC_ALLOWED_ALERT_EMAILS=you@example.com,cloud-cost-owner@example.com
```

For static export, this value is read at build time and embedded into the generated frontend files in `frontend/out/`:

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL="https://xyqayo8x14.execute-api.ap-south-1.amazonaws.com" \
NEXT_PUBLIC_ALLOWED_ALERT_EMAILS="you@example.com,cloud-cost-owner@example.com" \
npm run build
```

## Owner Routing

Resource-level findings read AWS tags and add `owner`, `owner_email`, and `environment` metadata when possible. Gmail alerts are grouped by `owner_email`, so different teams receive only their own findings.

Supported map keys:

- Direct owner or team name, for example `"platform"`.
- Environment name, for example `"prod"`.
- Environment and owner pair, for example `"prod:payments"`.
- Raw email address in an owner tag, for example `OwnerEmail=team@example.com`.

Example:

```hcl
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
