"""Live integration tests against the deployed cognito-auth-chatbot stack.

Manual / opt-in -- NOT part of the default `pytest backend/lambda/tests` run
(T1's Done-when). Run explicitly, from the repository root:

    read -rs TEST_USER_PASSWORD && export TEST_USER_PASSWORD
    uv run pytest backend/lambda/tests/test_integration.py -v -s
    unset TEST_USER_PASSWORD

Requires: `terraform apply` already run (T5), `TEST_USER_PASSWORD` set to the
current test user's password (never echoed).

**Run this suite exclusively.** It takes ~16 minutes wall clock and measures
the Lambda's `Invocations` metric to prove the authorizer never lets a
rejected request reach the function. Any other invocation during that
window -- a manual browser test, a second concurrent run -- adds to the
metric and produces a failure that reads exactly like a fail-open authorizer
bug but isn't one. A preflight check below aborts fast if the function was
already invoked in the preceding window, rather than running for 16 minutes
before discovering the run was contaminated.

Window A and Window B are two non-overlapping, sequential time ranges: this
file's own test order enforces that boundary (see AC-8/AC-9 and AC-10/AC-17).
"""
import json
import os
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TERRAFORM_DIR = Path(__file__).resolve().parents[3] / "infra" / "terraform"
REGION = "us-east-2"
USERNAME = "test-user@example.com"  # must match infra/terraform/scripts/provision-test-user.sh


def _tf_output(name: str) -> str:
    result = subprocess.run(
        ["terraform", "output", "-raw", name],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _aws_json(*args: str) -> dict:
    result = subprocess.run(
        ["aws", *args, "--output", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args)} failed: {result.stderr}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def _admin_initiate_auth(pool_id: str, client_id: str, username: str, password: str) -> dict:
    """Mint tokens via ADMIN_USER_PASSWORD_AUTH, password never in argv."""
    payload = {
        "UserPoolId": pool_id,
        "ClientId": client_id,
        "AuthFlow": "ADMIN_USER_PASSWORD_AUTH",
        "AuthParameters": {"USERNAME": username, "PASSWORD": password},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        input_path = f.name
    try:
        result = subprocess.run(
            [
                "aws", "cognito-idp", "admin-initiate-auth",
                "--cli-input-json", f"file://{input_path}",
                "--output", "json",
            ],
            capture_output=True,
            text=True,
        )
    finally:
        Path(input_path).unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"admin-initiate-auth failed: {result.stderr}")
    return json.loads(result.stdout)["AuthenticationResult"]


def _post_chat(api_url: str, token: str | None, body) -> tuple[int, dict]:
    data = body if isinstance(body, (bytes, str)) else json.dumps(body)
    if isinstance(data, str):
        data = data.encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{api_url}/chat", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw}


def _lambda_invocations_sum(function_name: str, start_iso: str, end_iso: str) -> float:
    result = _aws_json(
        "cloudwatch", "get-metric-statistics",
        "--namespace", "AWS/Lambda",
        "--metric-name", "Invocations",
        "--dimensions", f"Name=FunctionName,Value={function_name}",
        "--start-time", start_iso,
        "--end-time", end_iso,
        "--period", "300",
        "--statistics", "Sum",
        "--region", REGION,
    )
    # A missing "Datapoints" key means the call didn't return the shape we
    # expect at all (a real failure would have already raised in _aws_json);
    # an empty list is CloudWatch's normal, valid "no invocations" answer.
    points = result["Datapoints"]
    return sum(p["Sum"] for p in points) if points else 0.0


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def test_window_a_rejects_every_invalid_token_and_makes_no_invocation():
    pool_id = _tf_output("cognito_user_pool_id")
    wrong_audience_client = _tf_output("cognito_test_wrong_audience_client_id")
    short_ttl_client = _tf_output("cognito_test_short_ttl_client_id")
    api_url = _tf_output("api_invoke_url")
    function_name = _tf_output("lambda_function_name")
    password = os.environ["TEST_USER_PASSWORD"]

    # Preflight: fail fast if the function was invoked recently, rather than
    # running for 16 minutes before discovering the run was contaminated by
    # concurrent use (see module docstring).
    preflight_end = _now_iso()
    preflight_start = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 5 * 60)
    )
    recent = _lambda_invocations_sum(function_name, preflight_start, preflight_end)
    assert recent == 0, (
        f"Lambda was invoked {recent} time(s) in the last 5 minutes -- this "
        "suite must run exclusively (no concurrent browser/API use); see "
        "the module docstring."
    )

    window_start = _now_iso()

    # AC-8 member 1: no Authorization header.
    status, body = _post_chat(api_url, None, {"message": "hello"})
    assert status == 401, f"expected 401 with no auth header, got {status}"
    assert "message" in body

    # AC-8 member 2: malformed token.
    status, body = _post_chat(api_url, "not-a-real-token", {"message": "hello"})
    assert status == 401, f"expected 401 with malformed token, got {status}"
    assert "message" in body

    # AC-8 member 3: wrong-audience token (structurally valid, correctly
    # signed, but for a client not in the authorizer's audience list).
    wrong_tokens = _admin_initiate_auth(pool_id, wrong_audience_client, USERNAME, password)
    status, body = _post_chat(api_url, wrong_tokens["IdToken"], {"message": "hello"})
    assert status == 401, f"expected 401 with wrong-audience token, got {status}"
    assert "message" in body

    # AC-8 member 4: expired token, minted from the in-audience short-TTL
    # client so the failure is attributable to expiry, not audience.
    short_ttl_tokens = _admin_initiate_auth(pool_id, short_ttl_client, USERNAME, password)
    print("waiting 5.5 minutes for the short-TTL token to expire...")
    time.sleep(5.5 * 60)
    status, body = _post_chat(api_url, short_ttl_tokens["IdToken"], {"message": "hello"})
    assert status == 401, f"expected 401 with expired token, got {status}"
    assert "message" in body

    print("waiting 5 minutes to read the Invocations metric over Window A...")
    time.sleep(5 * 60)
    window_end = _now_iso()
    invocations = _lambda_invocations_sum(function_name, window_start, window_end)
    assert invocations == 0, (
        f"expected zero Lambda invocations during Window A (all requests rejected "
        f"by the authorizer), got {invocations}. If this suite ran concurrently "
        f"with any other use of the stack, that -- not a fail-open authorizer -- "
        f"is the most likely cause; re-run exclusively."
    )


def test_window_b_happy_path_contract_and_positive_control():
    api_url = _tf_output("api_invoke_url")
    pool_id = _tf_output("cognito_user_pool_id")
    primary_client = _tf_output("cognito_primary_client_id")
    function_name = _tf_output("lambda_function_name")
    password = os.environ["TEST_USER_PASSWORD"]

    window_start = _now_iso()

    tokens = _admin_initiate_auth(pool_id, primary_client, USERNAME, password)
    id_token = tokens["IdToken"]

    # AC-10, AC-17: valid token, valid body -> 200 / ChatResponse.
    status, body = _post_chat(api_url, id_token, {"message": "hello"})
    assert status == 200, f"expected 200 for a valid request, got {status}: {body}"
    assert "reply" in body and isinstance(body["reply"], str)

    # AC-20: empty message -> 400 / ErrorResponse.
    status, body = _post_chat(api_url, id_token, {"message": ""})
    assert status == 400
    assert "message" in body

    # AC-20: over-maxLength message -> 400. Derived from the contract's
    # bound (see contracts/openapi/chatbot.yaml ChatRequest.message.maxLength
    # and backend/lambda/app.py's _MAX_MESSAGE_LENGTH, which mirrors it).
    status, body = _post_chat(api_url, id_token, {"message": "a" * 2001})
    assert status == 400
    assert "message" in body

    # AC-20: extra unexpected property -> 400.
    status, body = _post_chat(api_url, id_token, {"message": "hello", "extra": "nope"})
    assert status == 400
    assert "message" in body

    print("waiting 5 minutes to read the Invocations metric over Window B...")
    time.sleep(5 * 60)
    window_end = _now_iso()
    invocations = _lambda_invocations_sum(function_name, window_start, window_end)
    # Positive control: proves Window A's zero reading wasn't vacuous.
    assert invocations >= 1, (
        f"expected at least one Lambda invocation during Window B (the valid "
        f"request should have invoked the function), got {invocations}"
    )


def test_lambda_resource_policy_scopes_invocation_to_this_api_route():
    """AC-18: the resource policy admits only this API's POST /chat route."""
    function_name = _tf_output("lambda_function_name")
    policy_result = _aws_json(
        "lambda", "get-policy",
        "--function-name", function_name,
        "--region", REGION,
    )
    policy = json.loads(policy_result["Policy"])
    statements = policy["Statement"]
    assert len(statements) == 1, f"expected exactly one resource-policy statement, got {len(statements)}"
    condition = statements[0].get("Condition", {})
    source_arn = condition.get("ArnLike", {}).get("AWS:SourceArn", "")
    assert "execute-api" in source_arn and source_arn.endswith("/POST/chat"), (
        f"resource policy's source ARN is not scoped to this API's POST /chat route: {source_arn}"
    )


def test_cors_and_app_client_configuration_posture():
    """AC-19: exact CORS posture and a secret-less, exact-URL, enumeration-suppressed primary client."""
    pool_id = _tf_output("cognito_user_pool_id")
    primary_client = _tf_output("cognito_primary_client_id")
    api_id = _tf_output("api_invoke_url").split("//")[1].split(".")[0]

    client_result = _aws_json(
        "cognito-idp", "describe-user-pool-client",
        "--user-pool-id", pool_id,
        "--client-id", primary_client,
        "--region", REGION,
    )
    client = client_result["UserPoolClient"]
    assert "ClientSecret" not in client, "primary client must not have a generated secret"
    assert client["CallbackURLs"] == ["http://localhost:5173/callback"]
    assert client["LogoutURLs"] == ["http://localhost:5173/callback"]
    assert client["PreventUserExistenceErrors"] == "ENABLED"

    api_result = _aws_json("apigatewayv2", "get-api", "--api-id", api_id, "--region", REGION)
    cors = api_result["CorsConfiguration"]
    assert cors["AllowOrigins"] == ["http://localhost:5173"]
    assert sorted(cors["AllowMethods"]) == ["OPTIONS", "POST"]
    assert cors["AllowCredentials"] is False


def test_self_signup_is_rejected():
    """AC-13: unauthenticated SignUp is rejected with NotAuthorizedException."""
    primary_client = _tf_output("cognito_primary_client_id")
    # Random, never-reused password: this call is asserted to fail, but if
    # the allow_admin_create_user_only guard ever regressed, a committed
    # literal here would create a real pool user with a repo-known password.
    throwaway_password = secrets.token_urlsafe(24) + "Aa1!"
    payload = {
        "ClientId": primary_client,
        "Username": "rejected-signup@example.com",
        "Password": throwaway_password,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        input_path = f.name
    try:
        result = subprocess.run(
            [
                "aws", "cognito-idp", "sign-up",
                "--cli-input-json", f"file://{input_path}",
                "--region", REGION,
                "--output", "json",
            ],
            capture_output=True,
            text=True,
        )
    finally:
        Path(input_path).unlink(missing_ok=True)
    assert result.returncode != 0
    assert "NotAuthorizedException" in result.stderr, result.stderr


def test_log_retention_and_no_secret_leakage():
    """AC-22: 14-day retention, and no message text or 'Bearer' in the log stream."""
    log_group = _tf_output("log_group_name")
    group_result = _aws_json(
        "logs", "describe-log-groups",
        "--log-group-name-prefix", log_group,
        "--region", REGION,
    )
    groups = [g for g in group_result.get("logGroups", []) if g["logGroupName"] == log_group]
    assert groups, f"log group {log_group} not found"
    assert groups[0].get("retentionInDays") == 14

    streams_result = _aws_json(
        "logs", "describe-log-streams",
        "--log-group-name", log_group,
        "--order-by", "LastEventTime",
        "--descending",
        "--max-items", "3",
        "--region", REGION,
    )
    streams = streams_result.get("logStreams", [])
    assert streams, (
        f"no log streams found in {log_group} -- Window B should have produced "
        "at least one; run this test after test_window_b, not standalone"
    )

    scanned_events = 0
    found_marker = False
    for stream in streams:
        events_result = _aws_json(
            "logs", "get-log-events",
            "--log-group-name", log_group,
            "--log-stream-name", stream["logStreamName"],
            "--region", REGION,
        )
        for event in events_result.get("events", []):
            scanned_events += 1
            message = event.get("message", "")
            if "status=200" in message:
                found_marker = True
            assert "hello" not in message, f"chat message text leaked into logs: {message!r}"
            assert "Bearer" not in message, f"bearer token leaked into logs: {message!r}"

    assert scanned_events > 0, f"no log events found across {len(streams)} stream(s) in {log_group}"
    assert found_marker, (
        "no log event matched the handler's own 'status=200' marker -- the "
        "no-leak assertions above may not have scanned a real chat request"
    )
