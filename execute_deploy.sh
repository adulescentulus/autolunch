#!/usr/bin/env bash
set -euo pipefail

cd lambda/tinchen
zip ../tinchen.zip ./*.py
cd $OLDPWD

cd cfn
aws cloudformation package --template aws-resources.yaml --s3-bucket ${S3_BUCKET_NAME} --output-template template-export.yaml
aws cloudformation deploy  --template-file=template-export.yaml --stack-name="${STACK_NAME}" --capabilities=CAPABILITY_NAMED_IAM