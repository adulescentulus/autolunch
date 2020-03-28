#!/usr/bin/env bash
set -euo pipefail

: "$S3_BUCKET_NAME"
: "$STACK_NAME"
: "$MAIL_SENDER"
: "$MAIL_RECIPIENT"

cd lambda/tinchen
zip ../tinchen.zip ./*.py
cd $OLDPWD

cd cfn
aws cloudformation package --template aws-resources.yaml --s3-bucket ${S3_BUCKET_NAME} --output-template template-export.yaml
aws cloudformation deploy  --template-file=template-export.yaml --stack-name="${STACK_NAME}" --capabilities=CAPABILITY_NAMED_IAM --parameter-overrides MailSender=${MAIL_SENDER} MailRecipient=${MAIL_RECIPIENT} 