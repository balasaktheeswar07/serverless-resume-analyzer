#!/bin/sh
set -e

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

BUCKET_NAME="${S3_BUCKET:-resume-uploads}"
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-resume-analyzer}"
ROLE_NAME="${LAMBDA_ROLE_NAME:-lambda-role}"
ZIP_FILE="/tmp/${FUNCTION_NAME}.zip"

awslocal s3 mb "s3://${BUCKET_NAME}" >/dev/null 2>&1 || true

awslocal iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document file:///opt/code/trust-policy.json >/dev/null 2>&1 || true

awslocal iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name resume-analyzer-lambda-policy \
  --policy-document file:///opt/code/lambda-policy.json >/dev/null

python3 - <<PY
import zipfile
from pathlib import Path

zip_file = Path("${ZIP_FILE}")
source = Path("/opt/code/lambda/handler.py")
with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(source, "handler.py")
PY

if awslocal lambda get-function --function-name "${FUNCTION_NAME}" >/dev/null 2>&1; then
  awslocal lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --zip-file "fileb://${ZIP_FILE}" >/dev/null
else
  awslocal lambda create-function \
    --function-name "${FUNCTION_NAME}" \
    --runtime python3.11 \
    --role "arn:aws:iam::000000000000:role/${ROLE_NAME}" \
    --handler handler.handler \
    --zip-file "fileb://${ZIP_FILE}" \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={LOCALSTACK_ENDPOINT=http://localhost.localstack.cloud:4566,AWS_ACCESS_KEY_ID=test,AWS_SECRET_ACCESS_KEY=test,AWS_DEFAULT_REGION=us-east-1}" >/dev/null
fi

echo "LocalStack ready: bucket=${BUCKET_NAME}, lambda=${FUNCTION_NAME}"
