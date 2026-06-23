#!/usr/bin/env bash
set -euo pipefail

# Initialize Terraform remote state backend (S3 + DynamoDB)
# Run once per environment before the first terraform init.

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENTS=("dev" "staging" "prod")

for ENV in "${ENVIRONMENTS[@]}"; do
  BUCKET="fabric-terraform-state-${ENV}"
  TABLE="fabric-terraform-locks-${ENV}"

  echo "[${ENV}] Creating S3 bucket: ${BUCKET}"
  if aws s3api head-bucket --bucket "${BUCKET}" --region "${REGION}" 2>/dev/null; then
    echo "[${ENV}] Bucket already exists"
  else
    aws s3api create-bucket \
      --bucket "${BUCKET}" \
      --region "${REGION}" \
      --create-bucket-configuration LocationConstraint="${REGION}" 2>/dev/null || \
    aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}"

    aws s3api put-bucket-versioning \
      --bucket "${BUCKET}" \
      --versioning-configuration Status=Enabled

    aws s3api put-bucket-encryption \
      --bucket "${BUCKET}" \
      --server-side-encryption-configuration '{
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
      }'
  fi

  echo "[${ENV}] Creating DynamoDB table: ${TABLE}"
  if aws dynamodb describe-table --table-name "${TABLE}" --region "${REGION}" 2>/dev/null; then
    echo "[${ENV}] Table already exists"
  else
    aws dynamodb create-table \
      --table-name "${TABLE}" \
      --attribute-definitions AttributeName=LockID,AttributeType=S \
      --key-schema AttributeName=LockID,KeyType=HASH \
      --billing-mode PAY_PER_REQUEST \
      --region "${REGION}"
  fi
done

echo "Backend initialization complete."
