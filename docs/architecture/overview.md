# Architecture Overview

## Areas and change guidance

| Area | Responsibility | Change guidance |
| --- | --- | --- |
| `frontend/` | React (Vite, TypeScript) SPA. Gates the chat UI behind Cognito Hosted UI login via `aws-amplify`; holds tokens in memory only (`src/auth/tokenStorage.ts`). | Auth flow lives in `src/auth/`; chat UI and the API client live in `src/chat/`. `frontend/.env.local` (git-ignored) is generated from `terraform output` — see `infra/terraform/README.md`. |
| `backend/lambda/` | Python Lambda behind API Gateway. `app.py` is the handler (parses/validates the request, never logs the event/token/message); `reply.py` is the pure rule-based reply function. | `tests/` holds fast unit tests (`pytest backend/lambda/tests`) plus the opt-in, live `tests/test_integration.py` (not part of the default run — see its docstring). |
| `infra/terraform/` | All AWS infrastructure: Cognito user pool (3 app clients), Lambda + IAM role, API Gateway HTTP API + JWT authorizer. | `README.md` in this directory is the canonical deploy/destroy runbook — don't restate its sequence elsewhere. |
| `contracts/openapi/` | The `POST /chat` interface contract. | Changing the request/response shape here must stay in sync with `backend/lambda/app.py` and `docs/specs/cognito-auth-chatbot/spec.md`'s Acceptance Criteria. |

## Entry points

- [`docs/specs/cognito-auth-chatbot/spec.md`](../specs/cognito-auth-chatbot/spec.md) — the feature's behavior contract and acceptance criteria.
- [`docs/specs/cognito-auth-chatbot/plan.md`](../specs/cognito-auth-chatbot/plan.md) — the implementation strategy and task breakdown.
- [`docs/adr/0001-cognito-auth-chatbot-stack.md`](../adr/0001-cognito-auth-chatbot-stack.md) — why Terraform, Cognito Hosted UI, Python, and the other stack choices were made.
