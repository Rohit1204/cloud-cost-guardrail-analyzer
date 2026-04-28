#!/usr/bin/env bash
# Build the static Next.js dashboard and deploy to the Terraform-managed S3 bucket + CloudFront.
#
# Prerequisites:
#   - AWS CLI configured (`aws sts get-caller-identity` works)
#   - Terraform applied at least once so outputs exist (`infra/terraform.tfvars`)
#   - Node.js and npm (uses `npm ci` when package-lock.json is present)
#
# Put API URLs and NEXT_PUBLIC_* vars in `frontend/.env.local` (they are baked in at build time).
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Options:
#   SKIP_CLOUDFRONT_INVALIDATION=1 ./deploy.sh   Skip CDN invalidation (faster, stale cache until TTL)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$ROOT/frontend"
INFRA="$ROOT/infra"

if [[ ! -d "$FRONTEND" ]]; then
  echo "error: frontend directory not found: $FRONTEND" >&2
  exit 1
fi

if [[ ! -d "$INFRA" ]]; then
  echo "error: infra directory not found: $INFRA" >&2
  exit 1
fi

echo "==> Installing frontend dependencies"
cd "$FRONTEND"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

echo "==> Building static export (reads frontend/.env.local if present)"
npm run build

echo "==> Reading Terraform outputs"
BUCKET="$(terraform -chdir="$INFRA" output -raw frontend_bucket_name)"
DIST_ID="$(terraform -chdir="$INFRA" output -raw frontend_cloudfront_distribution_id)"
URL="$(terraform -chdir="$INFRA" output -raw frontend_cloudfront_url)"

echo "==> Uploading to s3://$BUCKET/"
aws s3 sync "$FRONTEND/out/" "s3://${BUCKET}/" --delete

if [[ "${SKIP_CLOUDFRONT_INVALIDATION:-}" != "1" ]]; then
  echo "==> Invalidating CloudFront distribution $DIST_ID"
  aws cloudfront create-invalidation \
    --distribution-id "$DIST_ID" \
    --paths "/*" \
    --output text \
    --query "Invalidation.Id"
else
  echo "==> Skipping CloudFront invalidation (SKIP_CLOUDFRONT_INVALIDATION=1)"
fi

echo ""
echo "Deployed: $URL"
