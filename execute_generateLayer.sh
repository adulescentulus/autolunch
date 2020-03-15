#!/usr/bin/env bash
set -euo pipefail

mkdir -p lambda_layers/python/lib/python3.8/site-packages
pip install -r lambda_layers/requirements.txt -t lambda_layers/python/lib/python3.8/site-packages
cd lambda_layers/
zip -r autolunch_python.zip *
cd $OLDPWD