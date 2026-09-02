# frontend — cognito-auth-chatbot

React (Vite, TypeScript) SPA. See the root [`README.md`](../README.md) for
what the app does and [`docs/architecture/overview.md`](../docs/architecture/overview.md)
for where things live.

## Setup

Requires the backend already deployed (`infra/terraform/README.md`).

```bash
npm ci
```

### Environment (`.env.local`)

Git-ignored, generated from the deployed stack's `terraform output` — run
this from `infra/terraform/` after every `apply` or recreate:

```bash
cat > ../frontend/.env.local << EOF
VITE_COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
VITE_COGNITO_CLIENT_ID=$(terraform output -raw cognito_primary_client_id)
VITE_COGNITO_DOMAIN=$(terraform output -raw cognito_hosted_ui_domain)
VITE_API_URL=$(terraform output -raw api_invoke_url)
EOF
```

| Variable | Terraform output |
| --- | --- |
| `VITE_COGNITO_USER_POOL_ID` | `cognito_user_pool_id` |
| `VITE_COGNITO_CLIENT_ID` | `cognito_primary_client_id` |
| `VITE_COGNITO_DOMAIN` | `cognito_hosted_ui_domain` |
| `VITE_API_URL` | `api_invoke_url` |

If `.env.local` is missing or stale (e.g. after a `terraform destroy`/`apply`
recreate), `Amplify.configure` receives `undefined` values and the app shows
a permanently blank page — regenerate it and reload.

## Run

```bash
npm run dev
```

## Test

```bash
npm test        # vitest run
npx tsc -b      # typecheck
npx oxlint      # lint
```
