# cognito-auth-chatbot — infrastructure runbook

Deploys to AWS account `910929919874`, region `us-east-2`, using the
credential profile already active in your shell (`aws sts get-caller-identity`
must resolve before running any command below — no named profile switch is
used mid-run). The AWS provider also enforces this account via
`allowed_account_ids` in `versions.tf`.

**Prerequisites:** `terraform`, `aws` (authenticated), `jq` (used by
`scripts/provision-test-user.sh` to keep the test user's password out of any
process's argv).

**What this costs to leave running:** at this scale (one Cognito pool with
three app clients, one Lambda invoked only during manual testing, one HTTP
API), everything here fits within AWS's always-free tiers for Cognito MAUs,
Lambda requests/compute, and API Gateway HTTP API requests. There is no
meaningfully billable cost to leaving the stack up between sessions.

This is the **canonical runbook** for this feature — `plan.md`'s tasks
reference this sequence rather than restating it. Follow it exactly; do not
substitute a different command form (see the password-entry note below).

## First-time setup

```bash
cd infra/terraform
terraform init
```

## Apply (bring the stack up)

```bash
terraform plan            # preview
terraform apply           # creates: Cognito user pool + Hosted UI domain +
                           # 3 app clients, Lambda + IAM role/policy + log
                           # group, API Gateway HTTP API + JWT authorizer +
                           # route + stage + Lambda permission (15 resources)

# Readiness probe -- distinguishes "not yet propagated" from "misconfigured"
DOMAIN="$(terraform output -raw cognito_hosted_ui_domain)"
API_URL="$(terraform output -raw api_invoke_url)"
./scripts/wait-for-ready.sh "https://$DOMAIN"
./scripts/wait-for-ready.sh "$API_URL/chat" 120 POST 401

terraform plan             # confirm no drift (should report "No changes")
```

### Provisioning the pre-provisioned test user

The test user's password is never hardcoded, committed, or echoed, and is
never passed as a value argument to any process (including the AWS CLI) --
always enter it via a non-echoing prompt, never inline:

```bash
read -rs TEST_USER_PASSWORD && export TEST_USER_PASSWORD
./scripts/provision-test-user.sh
unset TEST_USER_PASSWORD
```

Never invoke as `TEST_USER_PASSWORD=<value> ./scripts/provision-test-user.sh`
-- that form is recorded in shell history.

### `checkov` review (informational, not gating)

```bash
uv run checkov -d infra/terraform/ --compact
```

Findings recorded as of the last review: all IAM/secrets checks pass
(least-privilege role, no hardcoded credentials, no full-access grants). The
following are known, accepted residuals -- controls this minimal demo does
not budget for, not oversights:

- `CKV_AWS_76` — API Gateway access logging not enabled.
- `CKV_AWS_338` / `CKV_AWS_158` — CloudWatch log group retention is 14 days
  (not 1 year) and not KMS-encrypted.
- `CKV_AWS_50` — Lambda X-Ray tracing not enabled.
- `CKV_AWS_117` — Lambda not placed in a VPC.
- `CKV_AWS_116` — Lambda has no Dead Letter Queue.
- `CKV_AWS_272` — Lambda code-signing not configured.
- `CKV_AWS_115` — Lambda has no reserved concurrency limit.

## Destroy and recreate (teardown / drift proof)

```bash
terraform destroy
terraform apply
./scripts/wait-for-ready.sh "https://$(terraform output -raw cognito_hosted_ui_domain)"
./scripts/wait-for-ready.sh "$(terraform output -raw api_invoke_url)/chat" 120 POST 401
read -rs TEST_USER_PASSWORD && export TEST_USER_PASSWORD
./scripts/provision-test-user.sh
unset TEST_USER_PASSWORD
```

## State-loss fallback (manual teardown)

Terraform state is local and unencrypted (no remote backend) -- an
accepted tradeoff at this scale (see `plan.md` Risks). If `.terraform` /
the state file is lost, remove resources manually via the AWS Console or
CLI, by name, in this account/region:

- Cognito user pool `cognito-auth-chatbot` (deletes its domain and all
  three app clients with it)
- Lambda function `cognito-auth-chatbot`
- IAM role `cognito-auth-chatbot-lambda-exec`
- CloudWatch log group `/aws/lambda/cognito-auth-chatbot`
- API Gateway HTTP API named `cognito-auth-chatbot`

## Frontend configuration

`frontend/.env.local` (git-ignored) must be regenerated from `terraform
output` after every `apply` or recreate, since app client IDs and the API
invoke URL change — see [`../../frontend/README.md`](../../frontend/README.md#environment-envlocal)
for the exact command and variable mapping.
