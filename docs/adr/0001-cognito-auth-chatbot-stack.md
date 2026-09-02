# ADR-0001: Stack choices for the Cognito-authenticated chatbot

- **Status:** Accepted <!-- moved from Proposed: the governing feature spec (docs/specs/cognito-auth-chatbot/spec.md) is Approved -->
- **Date:** 2026-08-31

## Context

This repository had no application code before this feature. Building the
first real feature — a login-gated chatbot — required picking a frontend
stack, an auth approach, a Lambda runtime, an IaC tool, a deployment region,
and a user-provisioning model, with no prior repository precedent to follow.

## Decisions

1. **Terraform, not AWS CDK or SAM.** Terraform (v1.14.8) was already
   installed in the development environment; neither the CDK CLI nor the SAM
   CLI was present (`cdk --version` / `sam --version` both returned "command
   not found"). Terraform also keeps infra declarative and provider-agnostic
   if the project later needs non-AWS resources.
2. **Cognito Hosted UI, not a custom login form.** The Hosted UI is
   AWS-managed, gets password reset and session handling for free, and
   removes an entire class of custom-auth-form bugs. The cost is less control
   over the login page's exact look — acceptable for a minimal chatbot demo,
   revisited only if styling becomes a real requirement later.
3. **Python for the Lambda, JavaScript/TypeScript for the React frontend.**
   Python matches the repository's only existing manifest (`pyproject.toml`,
   `requires-python >= 3.13`), even though that manifest is currently
   agent-tooling-only. Splitting language by layer (Python backend,
   JS/TS frontend) is the ecosystem-conventional choice for each side rather
   than forcing one language across both.
4. **Pre-provisioned users, no self-service sign-up.** The owner creates
   Cognito user accounts directly (Console, CLI, or `AdminCreateUser`); the
   Hosted UI exposes no public sign-up flow. This avoids email-verification
   flows, bot signups, and abuse-prevention work that a minimal demo doesn't
   need.
5. **Region `us-east-2`.** Chosen directly by the repository owner; no
   latency, compliance, or existing-resource constraint drove the choice.
6. **Session-only chat history, no server-side persistence.** The chat
   transcript lives in browser tab/session state only. This avoids
   introducing a database or cache for a feature whose objective is the
   login-gated round trip, not durable conversation history.
7. **`aws-amplify` for the Hosted UI authorization-code exchange, not a
   thinner OIDC client.** Amplify is AWS's own maintained library for this
   exact integration (Cognito Hosted UI + PKCE), at the cost of a larger
   transitive dependency tree than a minimal OIDC client would pull in for
   what is otherwise one redirect and one token exchange. Mitigated by
   committing `frontend/package-lock.json` and installing via `npm ci`
   (spec Boundaries) so the resolved tree stays reproducible and auditable.

## Consequences

- Adding self-service sign-up, a custom login UI, a real LLM backend, or
  persisted chat history are all separately scoped follow-on decisions, not
  part of this feature.
- The stack introduces new top-level directories `frontend/`, `backend/`,
  `infra/`, and `contracts/`, none of which existed in this repository
  before. `docs/adr/` (this file's own directory) is a new subtree of the
  already-existing `docs/`, not a new top-level directory.
- Real AWS resources are created in account `910929919874`; `infra/terraform/README.md`
  documents the apply/destroy/re-apply runbook so the stack can be torn down
  and recreated on demand.
