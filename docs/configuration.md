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
| `GMAIL_TOKEN_JSON` | empty | Authorized-user Gmail token JSON. |
| `GMAIL_TOKEN_FILE` | `gmail_token.json` | Local token file used when `GMAIL_TOKEN_JSON` is absent. |
| `WHATSAPP_ACCESS_TOKEN` | empty | Meta WhatsApp Cloud API access token. |
| `WHATSAPP_PHONE_NUMBER_ID` | empty | Meta phone number ID. |
| `WHATSAPP_TO` | empty | Recipient phone number in international format without `+`. |
| `WHATSAPP_API_VERSION` | `v19.0` | Meta Graph API version. |

## Terraform Variables

| Variable | Default | Description |
| --- | --- | --- |
| `aws_region` | `ap-south-1` | AWS region for Lambda and regional checks. |
| `project_name` | `cloud-cost-guardrail-bot` | Resource name prefix. |
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
| `gmail_token_json` | empty | Gmail OAuth token JSON. Sensitive. |
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
