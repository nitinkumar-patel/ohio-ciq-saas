#!/usr/bin/env bash
# Idempotently creates (or resets the password of) the one pre-provisioned
# Cognito test user used by T6/T9's manual and live verification.
#
# Reads the password from the required TEST_USER_PASSWORD environment
# variable -- never hardcoded, committed, or echoed. The password is never
# placed in any process's argv (including the AWS CLI child process): it is
# read directly from the environment by jq into a mode-600 temp file, fed to
# the AWS CLI via --cli-input-json file://<path>, and the temp file is
# removed immediately after use.
#
# Usage:
#   read -rs TEST_USER_PASSWORD && export TEST_USER_PASSWORD
#   ./provision-test-user.sh
#   unset TEST_USER_PASSWORD
#
# Never invoke as `TEST_USER_PASSWORD=<value> ./provision-test-user.sh` --
# that form is recorded in shell history.
set -euo pipefail

: "${TEST_USER_PASSWORD:?TEST_USER_PASSWORD must be set to a non-empty value (never inline -- use 'read -rs TEST_USER_PASSWORD && export TEST_USER_PASSWORD' first)}"

TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TERRAFORM_DIR"

POOL_ID="$(terraform output -raw cognito_user_pool_id)"
COGNITO_USERNAME="test-user@example.com"  # must match backend/lambda/tests/test_integration.py's USERNAME
export POOL_ID COGNITO_USERNAME

if aws cognito-idp admin-get-user --user-pool-id "$POOL_ID" --username "$COGNITO_USERNAME" >/dev/null 2>&1; then
  echo "provision-test-user: user already exists, resetting password"
else
  aws cognito-idp admin-create-user \
    --user-pool-id "$POOL_ID" \
    --username "$COGNITO_USERNAME" \
    --user-attributes Name=email,Value="$COGNITO_USERNAME" Name=email_verified,Value=true \
    --message-action SUPPRESS >/dev/null
  echo "provision-test-user: user created"
fi

password_input_json="$(mktemp)"
chmod 600 "$password_input_json"
trap 'rm -f "$password_input_json"' EXIT

jq -n '{UserPoolId: env.POOL_ID, Username: env.COGNITO_USERNAME, Password: env.TEST_USER_PASSWORD, Permanent: true}' \
  > "$password_input_json"
aws cognito-idp admin-set-user-password --cli-input-json "file://$password_input_json"
rm -f "$password_input_json"

echo "provision-test-user: password set"
