# Security Guide

Cloud Cost Guardrail Bot handles cloud inventory, billing data, and notification credentials. Treat local config and Terraform state as sensitive.

## Secrets

Never commit:

- `.env` or `.env.*`
- `credentials.json`
- `gmail_token.json`
- `*.tfvars`
- `*.tfvars.json`
- Terraform state files
- WhatsApp access tokens

The repository `.gitignore` excludes these by default.

## Terraform State

Terraform state can contain sensitive values, including Gmail OAuth JSON and WhatsApp tokens when provided as variables.

For production:

- Use an encrypted remote backend such as S3 with SSE-KMS.
- Enable state locking with DynamoDB or Terraform Cloud.
- Restrict state read access to trusted operators only.
- Avoid placing long-lived tokens directly in Terraform variables.

## Recommended Secret Management

The current demo supports environment variables for simplicity. Production should use AWS Secrets Manager:

- Store Gmail authorized-user token JSON in Secrets Manager.
- Store WhatsApp access token in Secrets Manager.
- Grant Lambda `secretsmanager:GetSecretValue` only for specific secret ARNs.
- Rotate tokens on a documented schedule.

## IAM Model

The Lambda role is read-only for cost and resource inspection. It does not have permissions to stop, delete, or resize resources.

Current AWS access categories:

- Cost Explorer read APIs.
- EC2 describe APIs.
- RDS describe APIs.
- CloudWatch metric read APIs.
- CloudWatch Logs write APIs.

For production, scope permissions further where possible and deploy through a controlled CI/CD role.

## OAuth Security

Gmail uses an OAuth authorized-user token. If credentials are exposed:

1. Revoke the OAuth grant from the Google account security page.
2. Rotate or delete the OAuth client secret in Google Cloud Console.
3. Regenerate `gmail_token.json`.
4. Update runtime secret storage.

## Data Handling

Alerts may contain resource IDs, service names, cost data, and suggested remediation actions. Send alerts only to trusted recipients and approved communication channels.

## Production Hardening Checklist

- Secrets moved to AWS Secrets Manager.
- Terraform state stored in encrypted remote backend.
- IAM permissions reviewed and least privilege confirmed.
- CloudWatch alarms configured for Lambda errors.
- Logs retention configured according to policy.
- OAuth credentials rotated and documented.
- No secrets present in git history.
