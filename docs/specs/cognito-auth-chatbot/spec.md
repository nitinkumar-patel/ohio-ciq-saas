# Spec: Cognito-Authenticated Chatbot

- **Status:** Shipped <!-- Draft | Approved | Implementing | Shipped | Archived -->
- **Owner:** repository owner
- **Plan:** [`plan.md`](plan.md)
- **Constrained by:** ADR-0001
- **Brief:** none
- **Discovery:** none
- **Contract:** contracts/openapi/chatbot.yaml
- **Shape:** mixed

> **Spec contract:** this document defines what "done" means. The implementing
> PR must match this spec, or update it. Verification must be derivable from it.

## Objective

A pre-provisioned user, running the React app via its local development
server against the live, deployed backend, logs into it through AWS
Cognito's Hosted UI, and once authenticated can exchange chat messages with a
bot backed by an AWS Lambda function invoked through API Gateway. Every
request to the chat API carries the user's Cognito-issued token, and API
Gateway rejects any request that doesn't. Success looks like: a user who
isn't logged in never sees the chat screen, not even briefly; a user who is
logged in can type a message, see it appear in the transcript, and see the
bot's reply appear next to it; and no chat traffic reaches the Lambda without
a valid token. This spec covers the login-gated round trip only — it treats
the bot's reply as a small, rule-based response engine (not a
general-purpose AI backend) whose replies vary by input, and it stops at
running the frontend locally against the real backend (see Boundaries and
Follow-ons for what's excluded).

## Durable Outputs

| Semantic role | Applicability | Destination | Owner | Expected evidence | Closeout condition |
| --- | --- | --- | --- | --- | --- |
| Interface compatibility | Applicable — this feature defines the repo's first HTTP API surface | `contracts/openapi/chatbot.yaml` | Feature owner | OpenAPI document describing `POST /chat`, its Cognito-authorizer security scheme, request/response schemas, and error responses | Contract committed, `x-spec` back-reference to this spec present, and the deployed API matches it (AC-17) |
| Current architecture | Applicable — repo has no populated architecture doc and this is its first real code | `docs/architecture/overview.md` | Feature owner | Areas table names `frontend/`, `backend/lambda/`, `infra/terraform/` and their responsibilities | Doc reflects the actual final directory layout, no placeholders remain |
| Current product truth | Not applicable | — | — | — | `docs/product/roadmap.md` is a repository-wide, multi-quarter planning artifact. Filling it in is not a byproduct of shipping this one feature — it stays pre-existing scaffold debt, out of this feature's scope. |
| Architecture golden path | Not applicable | — | — | — | `docs/architecture/reference.md` does not exist yet. A single-feature, greenfield repository has no golden path to hold future work to; `docs/architecture/overview.md` (above) is the correct home for this feature's architecture facts at the repo's current scale. |
| Decision rationale | Applicable — several load-bearing choices (Terraform over CDK/SAM, Hosted UI over custom login, pre-provisioned users over self-service, Python Lambda, `us-east-2`) need a durable "why" | `docs/adr/0001-cognito-auth-chatbot-stack.md` | Feature owner | ADR recording the decision, alternatives considered, and consequences | ADR moves from `Proposed` to `Accepted` at the same time this spec moves to `Approved` — it is not a separate approval |
| Operations | Applicable — this deploys real, billable AWS resources and the user asked for a repeatable teardown/recreate path | `infra/terraform/README.md` | Feature owner | Documented `terraform init/plan/apply/destroy` commands, the committed test-user provisioning script with its non-echoing `read -rs`/`export`/`unset` password-entry sequence written out in the runbook itself, the AWS credential mechanism used, required region (`us-east-2`), and a note on what each resource costs to leave running | Runbook's `apply` → smoke test → `destroy` → `apply` cycle is actually exercised once, not just written |
| Release history | Applicable — first user-visible change to ship from this repo | `docs/product/changelog.md` | Feature owner | `## [cognito-auth-chatbot][0.1.0] — <ship date>` entry (dated when `spec.md` actually ships, not when this spec was drafted) describing the login-gated chatbot | Entry present at the same time `spec.md` moves to `Shipped` |
| User-facing promise | Applicable — root `README.md` is currently empty and a working app now exists | `README.md` | Feature owner | Short section: what the app is, how to log in (pre-provisioned Cognito user), how to send a message, and that it runs via a local dev server against the real deployed backend | README accurately describes the shipped flow |
| User documentation (guides) | Not applicable | — | — | — | This is a localhost-only demo with one flow and one user type; the `README.md` section above is the complete user-facing surface. A `docs/guides/` entry is unwarranted until the app has real end-user hosting (see Follow-ons) |
| Maintainer procedure | Not applicable | — | — | — | `AGENTS.md` already routes all repository changes through `work-loop`; no new procedure is introduced by this feature |
| Reusable learning | Not applicable as a separate file | — | — | — | Captured through `work-loop`'s built-in `Capture learnings` / `project-knowledge` step at DECIDE, not a standalone doc |

## Boundaries

### Always do

- Gate the chat UI behind a valid Cognito session; never render the chat screen for an unauthenticated user, including transiently before a redirect completes.
- Use the Cognito Hosted UI (managed login pages) for sign-in/sign-out — no custom-built login form. Any Cognito app-client auth flow used purely for IAM-gated test tooling (never reachable by an anonymous end user) is a bounded exception, not a second sign-in path (see plan Risks).
- Write the Lambda in Python; write the React app in TypeScript (Vite `react-ts` scaffold) under `frontend/`, the Lambda under `backend/lambda/`, and all infrastructure as Terraform under `infra/terraform/`.
- Keep chat transcript state client-side only, scoped to the current browser tab/session; never send it to, or store it in, any backend datastore.
- Give the Lambda's IAM execution role only the permissions it needs to run and write its own logs (least privilege) — no wildcard resource or action grants.
- Deploy to the `us-east-2` AWS region.
- Run `checkov -d infra/terraform/` once against the applied configuration (T5) and review its findings; fix anything that reflects a real gap against this feature's own stated security posture (least-privilege IAM, no public exposure beyond the intended `POST /chat` route, no self-service sign-up). A finding outside that scope (e.g. MFA, WAF, access logging, VPC placement — controls this minimal demo does not budget for) may be left unresolved, recorded in `infra/terraform/README.md`, rather than blocking the feature; `checkov` is informational here, not a pass/fail gate, because this feature does not define a severity-tier or suppression policy. The separate, mandatory `security-reviewer` pass (see Assumptions) is this feature's actual security gate.
- Log only the request ID and the outcome (status code) from the Lambda; never log the raw event, the `Authorization` header, or chat message text — CloudWatch Logs is not a chat-history store (see the session-only Never-do above).
- Commit `frontend/package-lock.json` and install frontend dependencies via `npm ci`, so the resolved dependency tree (including `aws-amplify`'s transitive surface) is reproducible and auditable.

### Ask first

- Before running `terraform apply` against AWS account `910929919874`.
- Before running `terraform destroy` against AWS account `910929919874`.
- Before adding any *direct* dependency beyond the set `plan.md` names: frontend — the Vite `react-ts` scaffold's own dependencies (`react`, `react-dom`, `typescript`, `@vitejs/plugin-react`), `aws-amplify`, and `vitest` + `@testing-library/react` + `jsdom` (dev, for AC-2's component test — `jsdom` supplies vitest's DOM test environment); backend — the Python standard library plus `pytest` (dev) and `checkov` (dev). Transitive dependencies these pull in are not subject to this gate.
- Before widening the Lambda's IAM role beyond what its own code path requires.

### Never do

- Never enable Cognito self-service sign-up; every user account is pre-provisioned by the owner outside the app (Console, CLI, or `AdminCreateUser` API).
- Never commit AWS credentials, Cognito app-client secrets, any Cognito user's password, or `.tfstate`/`.terraform/`/generated env files to the repository.
- Never introduce a persistence layer (database, cache, file store) for chat messages — this spec's chat history is session-only by design.
- Never add a new top-level directory beyond `frontend/`, `backend/`, `infra/`, and `contracts/` without a spec/plan amendment. (`docs/adr/` is a subtree of the already-existing `docs/`, not a new top-level directory, and is exempt from this rule.)
- Never call a real or simulated LLM provider from the Lambda — the bot's reply is a fixed rule-based function, not a model call.
- Never provision static-site hosting (S3 website, CloudFront, Amplify Hosting) for the React app under this spec — the frontend is verified via its local dev server against the real deployed Cognito/API Gateway/Lambda stack; hosting it is out of scope (see Follow-ons).
- Never mutate a Terraform-managed Cognito resource (app client, user pool) via the AWS CLI or Console — auth-flow configuration lives in Terraform only, so a `destroy`/`apply` cycle can't silently diverge from it (see plan T2, T5).

## Testing Strategy

- **Lambda response logic** (AC-6, AC-7): **TDD**. `generate_reply` is a pure function with a compressible invariant (same input → same reply; different qualifying inputs → different replies), unit-tested directly, independent of API Gateway or AWS. (See plan T1 for why the exact stub is authored later, at `work-loop`'s own PLAN step, rather than here.)
- **No pre-redirect content flash** (AC-2): **TDD** at the component level (the app's root renders nothing while the auth check is pending), confirmed a second time as part of the AC-1/AC-3 manual pass below — a human watching a redirect can miss a brief flash, so the mechanical check is the one that actually closes this criterion.
- **Authorizer rejection** (AC-8, AC-9, AC-17's 401 member): **goal-based check**, exercised as an **integration test**, run in a dedicated **Window A**: issue each enumerated rejected-token condition, then wait 5 minutes and read the Lambda's `Invocations` metric sum over Window A, asserting 401 on every call (each 401 body validated against the contract's `ErrorResponse` schema — AC-17) and a zero-or-absent sum for the window.
- **Authorizer happy path and contract conformance** (AC-10, AC-17's 200/400 members, AC-18, AC-19, AC-20, AC-22): **goal-based check**, exercised as an **integration test**, run in a separate, later **Window B** (never overlapping Window A) — a valid-ID-token call asserting 200 and a body matching the contract, an oversized/extra-field body asserting 400 (AC-20), a `get-policy` inspection confirming the Lambda's resource policy scopes invocation to this API's route (AC-18), a check of the deployed CORS/app-client configuration (AC-19), and a check of the log group's `retention_in_days` plus a scan of the resulting log stream for message text or the string "Bearer" (AC-22). Window B's valid-token call also doubles as the positive control proving Window A's "no increase" reading isn't vacuous.
- **No self-service sign-up** (AC-13): **goal-based check**, exercised as an **integration test** — a direct, unauthenticated call to the Cognito `SignUp` API using the app client ID, asserting the specific `NotAuthorizedException` rejection. (Not manual QA: a hidden or unlinked Hosted UI element would pass a purely visual check while the underlying API still accepted sign-ups.)
- **Login gating and chat UI flow** (AC-1, AC-2 confirmatory pass, AC-3, AC-4, AC-5, AC-11, AC-12, AC-21): **visual/manual QA**, exercised as an **end-to-end (E2E)** pass through the real deployed stack in a browser — attempt access while logged out, log in via the real Hosted UI with the pre-provisioned test user, send a message, sign out and confirm the app holds no tokens, close and reopen the tab, and confirm both that no prior client state remains (checked across `localStorage`, `sessionStorage`, IndexedDB, and cookies) and that a fresh credential prompt (not a silent SSO redirect) is required.
- **Infra provisioning, idempotence, and teardown** (AC-14, AC-15, AC-16): **infra/deploy mode** — `terraform plan` (preview) → `terraform apply` (convergent apply, gated on a readiness probe rather than apply's own exit code) → a second `terraform plan` proving no further changes → a `checkov` review (informational, see Boundaries) → the integration tests above running against the live stack (active smoke) → `terraform destroy` followed by a second `terraform apply`, the committed test-user provisioning script, the same checks again, and one manual round trip through the frontend (rollback/recreate proof).
- **Stubs:** 2 covered (AC-6, AC-7 — T1's `generate_reply`, `stub: true`); 1 `no stub (implementation-discovered)` (AC-2 — T7's pending-auth render, discovery predicate recorded in plan.md); all other TDD-eligible-looking criteria are goal-based or manual-QA mode and carry no stub obligation.

## Acceptance Criteria

- [x] **AC-1.** Given a user who is not logged in, when they open the React app, they are redirected to the Cognito Hosted UI login page.
- [x] **AC-2.** Given a user who is not logged in, when they open the React app, the chat screen is not rendered at any point before the Hosted UI redirect completes.
- [x] **AC-3.** Given a pre-provisioned user completes login through the Cognito Hosted UI with valid credentials, when Cognito redirects back to the React app, the user sees the chat screen.
- [x] **AC-4.** Given an authenticated user on the chat screen, when they submit a message, the message they typed appears in the chat transcript attributed to them.
- [x] **AC-5.** Given an authenticated user has submitted a message, when the Lambda's response is returned, the response text appears in the chat transcript attributed to the bot.
- [x] **AC-6.** Given the same input message text, when the Lambda processes it more than once, it returns the same reply text each time.
- [x] **AC-7.** The Lambda's reply is not a single constant string for every input — at least two distinct input messages produce two distinct reply texts.
- [x] **AC-8.** Given a request to the chat API endpoint whose bearer token is missing, malformed, expired, or issued for a different app client's audience, when API Gateway processes it, the caller receives an HTTP 401 response.
- [x] **AC-9.** Given any of the rejected-request conditions in AC-8, the Lambda function's `Invocations` metric shows no increase when measured over the 5 minutes following the request.
- [x] **AC-10.** Given a request to the chat API endpoint carrying a valid, unexpired Cognito ID token for a pre-provisioned user, when API Gateway processes it, the caller receives an HTTP 200 response.
- [x] **AC-11.** Given an authenticated user closes and reopens the browser tab, no client-held state — chat transcript, ID token, or refresh token — survives the closure.
- [x] **AC-12.** Given the user closes and reopens the tab and the app redirects them to log in again, the Cognito Hosted UI requires them to re-enter credentials rather than silently completing an existing SSO session.
- [x] **AC-13.** Given an unauthenticated call to the Cognito user pool's `SignUp` API using the app client ID, the call is rejected with `NotAuthorizedException`.
- [x] **AC-14.** Given a clean Terraform state, when `terraform apply` runs against AWS account `910929919874` in `us-east-2`, the Cognito user pool, Lambda function, and API Gateway are all created successfully.
- [x] **AC-15.** Given the infrastructure from AC-14 is applied, when `terraform plan` runs immediately afterward with no other changes made, it reports no further changes.
- [x] **AC-16.** Given `infra/terraform/README.md` already documents the destroy-and-recreate sequence before this criterion is exercised, when `terraform destroy` runs and `terraform apply` runs again immediately after using only that pre-existing documented sequence, the recreated stack passes the complete live integration-test suite that verifies this API (the same suite AC-8, AC-9, AC-10, AC-13, AC-17, AC-18, AC-19, AC-20, and AC-22 are checked by), and one authenticated chat round trip from the local frontend succeeds against it, with no step performed outside that documented sequence.
- [x] **AC-17.** The `POST /chat` request body and each of its 200, 400, and 401 response bodies conform to the schemas defined in `contracts/openapi/chatbot.yaml`.
- [x] **AC-18.** The Lambda function's resource policy grants invocation rights only to this API's `POST /chat` route — no other API Gateway route or AWS account can invoke it through that policy.
- [x] **AC-19.** The deployed HTTP API accepts cross-origin requests only from `http://localhost:5173` for `POST` and `OPTIONS` with credentials not allowed, and the primary Cognito app client has no generated secret, exact (non-wildcard) callback and logout URLs, and user-existence errors suppressed on authentication attempts.
- [x] **AC-20.** Given a `POST /chat` request whose `message` violates the contract's length bounds (empty, or over the maximum), or whose body carries a property the contract does not define, the caller receives an HTTP 400 response matching `ErrorResponse`.
- [x] **AC-21.** Given an authenticated user signs out, the app holds no ID or refresh token afterward in `localStorage`, `sessionStorage`, IndexedDB, or a cookie, and loading the app again requires a fresh Cognito Hosted UI credential prompt.
- [x] **AC-22.** The Lambda's CloudWatch log group retains logs for 14 days, and after processing a chat message its log stream contains neither the message text nor the string "Bearer".

## Follow-ons

The following are informal scope notes captured for a future session's
attention. None are filed as dispatchable `work-intake` items and none carry
a stable tracking reference — treat them as ideas to re-evaluate, not
committed or scheduled work:

- Replacing the rule-based Lambda reply with a real LLM call (e.g. Bedrock or an external provider).
- Persisting chat history server-side across sessions/devices.
- Self-service Cognito sign-up with email verification, if the app moves beyond pre-provisioned demo users.
- A custom in-app login form, if the Hosted UI's default styling stops being acceptable.
- Deploying the React app to real static hosting (S3+CloudFront or Amplify Hosting) instead of running it via a local dev server against the live backend.
- Accepting Cognito access tokens (not just ID tokens) on `POST /chat`, if a future client needs that.

## Assumptions

- Technical: Node.js v22.22.3 / npm 10.9.8 available locally (source: probe `node --version`, `npm --version`).
- Technical: Terraform v1.14.8 installed locally; no AWS CDK or SAM CLI found (source: probe `terraform --version`; `cdk --version` and `sam --version` → command not found) — Terraform is the IaC tool.
- Technical: AWS CLI is authenticated against account `910929919874` as IAM user `aiengineer`, using the default AWS CLI profile/credential chain — no named profile switch happens mid-implementation (source: probe `aws sts get-caller-identity`).
- Technical: repository has no existing frontend, backend, or IaC code; this spec establishes `frontend/`, `backend/lambda/`, and `infra/terraform/` from scratch (source: repo tree listing).
- Technical: no IaC security scanner (`tfsec`, `checkov`, `trivy`) was found locally (source: probe — all three report "command not found"); `checkov` is added as a task-zero dependency (pip-installable, no compiled binary needed) rather than assumed present.
- Technical: a Cognito user pool with `AdminCreateUserConfig.AllowAdminCreateUserOnly = true` rejects an unauthenticated `SignUp` call with `NotAuthorizedException` (source: AWS documentation on `AdminCreateUserConfigType`, docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminCreateUserConfigType.html).
- Technical: visiting Cognito's Hosted UI `/logout` endpoint (via browser redirect, not XHR) clears the "cognito" session cookie the Hosted UI otherwise keeps for up to 1 hour, so the next `/oauth2/authorize` redirect requires fresh credentials rather than silently continuing that session (AC-12) (source: AWS documentation, docs.aws.amazon.com/cognito/latest/developerguide/logout-endpoint.html; and repost.aws/knowledge-center/cognito-logout-endpoint-globalsignoutapi on the 1-hour cookie lifetime).
- Technical: Cognito's app-client `id_token_validity` can be set as low as 5 minutes (its documented minimum), which is used to produce AC-8's "expired token" member deterministically rather than guessing at a wait time (source: general Cognito app-client token-validity behavior; verified against the Terraform `aws_cognito_user_pool_client` schema at implementation time).
- Technical: `checkov`'s open-source (non-platform-connected) output is not confirmed to expose per-check severity tiers; this spec avoids depending on that by treating `checkov` as informational rather than a HIGH/CRITICAL-gated acceptance criterion (source: unverified — no network check available for Checkov's exact OSS severity behavior; the informational-only Boundaries wording is deliberately written to not depend on the answer).
- Technical: an API Gateway HTTP API JWT authorizer's `audience` accepts a list of client IDs, so a short-lived (5-minute `id_token_validity`) app client can be added alongside the primary client's ID to let a token from that client pass the audience check while still being independently mintable-and-expirable for AC-8's "expired" case — kept separate from the (still out-of-audience) client used for AC-8's "wrong audience" case, since the same client cannot demonstrate both failure modes (source: decided during this spec's fourth revision, after the pre-EXECUTE `adversarial-reviewer`/`security-reviewer` passes found the original single second-client design made the two cases indistinguishable).
- Technical: the pre-provisioned test user's password is read by `provision-test-user.sh` from a required environment variable at run time, never hardcoded or echoed; the script fails loudly if the variable is unset (source: decided during this spec's fourth revision, in response to the `security-reviewer` pass).
- Process: `frontend/package-lock.json` is committed and frontend installs use `npm ci`, so `aws-amplify`'s resolved dependency tree stays reproducible and auditable, per the `security-reviewer` pass's supply-chain finding (source: decided during this spec's fourth revision).
- Technical: AWS API Gateway HTTP API JWT authorizers validate the `aud` claim on ID tokens and the `client_id` claim on access tokens against the same configured audience list; this spec accepts only ID tokens (AC-10) and leaves access-token acceptance as an unverified, unused property of the mechanism (see Follow-ons) (source: AWS API Gateway HTTP API JWT authorizer troubleshooting documentation, docs.aws.amazon.com/apigateway/latest/developerguide/http-api-troubleshooting-jwt.html).
- Technical: AWS Lambda's `python3.13` managed runtime exists and is available in all commercial regions including `us-east-2` (source: aws.amazon.com/about-aws/whats-new/2024/11/aws-lambda-support-python-313).
- Technical: `aws_apigatewayv2_authorizer` with `authorizer_type = "JWT"`, an issuer built from the Cognito user pool's endpoint, and the app client ID as audience is the standard, working Terraform pattern for gating an HTTP API with Cognito (source: web search — andrewtarry.com/posts/aws-http-gateway-with-cognito-and-terraform; terraform-aws-modules/terraform-aws-apigateway-v2 `examples/complete-http`).
- Technical: Lambda runtime language is Python, matching the repo's existing `pyproject.toml` (`requires-python >= 3.13`) even though that manifest is currently agent-tooling-only, not app code (source: user confirmation 2026-08-31).
- Technical: chat transcript lives only in browser tab/session state; nothing is persisted server-side (source: user confirmation 2026-08-31).
- Product: bot response is a fixed rule-based function whose output varies by input; no external LLM call (source: user confirmation 2026-08-31; input-variance narrowed while drafting this spec's second revision, see AC-7).
- Product: auth UX uses the Cognito Hosted UI redirect flow, not a custom in-app login form (source: user confirmation 2026-08-31).
- Product: Cognito users are pre-provisioned by the owner; the Hosted UI has no public self-service sign-up (source: user confirmation 2026-08-31).
- Product: static hosting for the React app (S3+CloudFront, Amplify Hosting) is out of scope; the app runs via its local dev server against the real deployed Cognito/API Gateway/Lambda stack for verification. This narrows the Objective's promise to "the owner exercises the flow from a local dev server," not a hosted product any end user can reach (source: scope decision made while drafting this spec, not separately asked — flagged here for explicit objection at spec approval).
- Process: deployment region is `us-east-2` (source: user confirmation 2026-08-31).
- Process: "done" includes a real Terraform deploy to AWS account `910929919874`, gated by explicit confirmation immediately before any `terraform apply` or `terraform destroy` (source: user confirmation 2026-08-31); the plan includes a documented teardown-and-recreate path, driven by a committed provisioning script rather than ad hoc CLI steps, so the stack can be torn down and stood back up on demand without configuration drift.
- Process: `AGENTS.md` designates `work-loop` as the governing workflow; the auth/security-boundary and structural-change risk triggers route this feature through full mode (source: `AGENTS.md`; `work-loop` `SKILL.md` risk-triggers section). `work-loop`'s mandatory `security-reviewer` pass on infra-flavored work (spec stage and diff) is this feature's actual security gate; the informational `checkov` review in Boundaries does not substitute for it.
- Process: `docs/CONVENTIONS.md`'s requirement that a new top-level `contracts/` directory route through an RFC is treated as satisfied by this spec's own approval: `CONVENTIONS.md` is itself an unadopted seed document in this repository (per `AGENTS.md`: "optional starting point to adopt with maintainer approval, not an authority that outranks existing guidance"), no `new-rfc`-equivalent skill is installed, and approving `spec.md` is understood to include approving `contracts/openapi/` as a new top-level directory under that convention. If the owner does not want `CONVENTIONS.md` treated as binding, or objects to this reading, say so at approval and this spec is revised before proceeding (source: decided while drafting this spec's third revision, standing for confirmation at spec approval rather than left open indefinitely).
- Process: the experience-design pack (`creative-direction` / `design-review`) is not installed in this environment, so the chat screen's Acceptance Criteria are behavior-only; design intent for this surface is ungrounded and not separately verified.
- Process: this spec/plan went through two rounds of mandatory pre-EXECUTE `adversarial-reviewer` and `security-reviewer` passes (after the owner's initial approval) before implementation began; sustained findings from both rounds are folded into this text and `plan.md`'s Changelog, including AC-18 through AC-22 and the log-retention, password-entry, and Terraform-lock-file controls (source: `.context/reviews/7fd6e89f-7c70-48fb-897f-09aaa93064d2/`, session-local and gitignored).
- Technical: the Lambda's CloudWatch log group retention is set to 14 days — a value chosen for this demo's scale, not derived from a compliance requirement (source: decided during this spec's fourth revision, in response to the `security-reviewer` pass naming the retention as previously unbounded).
