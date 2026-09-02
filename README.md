# ohio-ciq-saas

A minimal, Cognito-authenticated chatbot. A pre-provisioned user logs in
through AWS Cognito's Hosted UI, then exchanges chat messages with a
rule-based bot running on AWS Lambda behind API Gateway. See
[`docs/specs/cognito-auth-chatbot/spec.md`](docs/specs/cognito-auth-chatbot/spec.md)
for the full feature contract.

## Running it

The backend (Cognito, Lambda, API Gateway) is deployed via Terraform — see
[`infra/terraform/README.md`](infra/terraform/README.md) for the deploy
runbook. Once deployed, run the frontend locally against the real backend:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. You'll be redirected to the Cognito Hosted UI
to log in.

**Logging in:** users are pre-provisioned by the repository owner (no
public sign-up) — see `infra/terraform/scripts/provision-test-user.sh`.

**Sending a message:** once logged in, type a message and press Send (or
Enter). The bot's reply appears below it. Chat history is not saved — it
lives only in that browser tab for the session.

**Signing out:** click "Sign out" to end the session immediately, or just
close the tab — either way, the next visit requires logging in again.

## Repository layout

See [`docs/architecture/overview.md`](docs/architecture/overview.md).
