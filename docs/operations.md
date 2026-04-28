# Operations Runbook

This runbook covers routine checks, troubleshooting, and operational response.

## Routine Health Checks

Local API:

```bash
curl http://127.0.0.1:8000/health
```

Deployed Lambda logs:

```bash
aws logs tail /aws/lambda/cloud-cost-guardrail-bot \
  --region ap-south-1 \
  --since 1h
```

Manual Lambda invoke:

```bash
aws lambda invoke \
  --region ap-south-1 \
  --function-name cloud-cost-guardrail-bot \
  response.json
```

## Common Errors

### Cost Explorer access denied

Symptom:

```text
AccessDeniedException: User not enabled for cost explorer access
```

Action:

- Enable Cost Explorer in the payer account.
- Confirm the caller has `ce:GetCostAndUsage`.
- Wait for Cost Explorer activation if it was just enabled.

### Cost Explorer data unavailable

Symptom:

```text
DataUnavailableException: Data is not available
```

Action:

- Wait for AWS billing data ingestion.
- Try a wider or older date range.
- Confirm the account has billable usage.

### Gmail token invalid

Symptom:

```text
invalid_grant
unauthorized_client
```

Action:

- Regenerate `gmail_token.json` with `scripts/generate_gmail_token.py`.
- Confirm Gmail API is enabled.
- Confirm OAuth consent screen and scopes include `https://www.googleapis.com/auth/gmail.send`.

### WhatsApp delivery failure

Action:

- Check `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, and `WHATSAPP_TO`.
- Confirm the recipient is allowed in the Meta test environment.
- Check Meta Graph API response in Lambda logs.

### Alert sent to default owner

Symptom:

```text
Owner route: unassigned / cloud-cost-owner@example.com
```

Action:

- Add `OwnerEmail`, `Owner`, or `Team` tags to the resource.
- Add `Environment` or `Stage` tags to improve context.
- Add an `OWNER_EMAIL_MAP` entry for team names that are not email addresses.
- Keep `DEFAULT_OWNER_EMAIL` set to a monitored mailbox so untagged findings are not dropped.

## Alert Triage

For every alert:

1. Confirm resource ownership from tags, account context, and workload name.
2. Validate whether the resource is production, staging, development, or abandoned.
3. For deletion recommendations, snapshot or backup first where appropriate.
4. Apply remediation manually.
5. Tag intentional exceptions with an owner and expiry date.

## Observability Improvements

Recommended production additions:

- Emit structured JSON logs for each detector result.
- Add CloudWatch metric filters for detector errors and notification failures.
- Create alarms for repeated Lambda failures.
- Send operational failure alerts to a separate incident channel.

## Release Process

1. Run unit tests.
2. Run Terraform formatting and validation.
3. Review changes for secrets.
4. Open a pull request and wait for CI.
5. Apply Terraform from a controlled environment.
6. Invoke Lambda manually and verify CloudWatch Logs.
