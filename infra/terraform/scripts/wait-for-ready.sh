#!/usr/bin/env bash
# Polls a URL with bounded backoff until it responds, or exits non-zero on
# timeout. Used to distinguish "not yet propagated" from "misconfigured"
# right after a Terraform apply, before running any real check against the
# Hosted UI domain or the API invoke URL.
#
# Usage: wait-for-ready.sh <url> [max_wait_seconds] [method] [expected_status]
#
# Without expected_status, any non-connection-error response counts as
# "ready" (used for the Hosted UI domain -- DNS/TLS/CloudFront reachability
# is the only thing being proven there). Pass expected_status to require an
# exact code -- e.g. for the API invoke URL's /chat route, a bare GET/POST
# with no Authorization header only proves the route and JWT authorizer are
# actually live if it returns exactly 401; a 404 means the route doesn't
# exist yet, which "any response" would otherwise wrongly accept as ready.
set -euo pipefail

url="${1:?usage: wait-for-ready.sh <url> [max_wait_seconds] [method] [expected_status]}"
max_wait="${2:-120}"
method="${3:-GET}"
expected_status="${4:-}"
interval=5
elapsed=0

while (( elapsed < max_wait )); do
  status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 -X "$method" "$url" 2>/dev/null)" || status="000"
  if [[ "$status" != "000" ]]; then
    if [[ -z "$expected_status" || "$status" == "$expected_status" ]]; then
      echo "wait-for-ready: $url responded with HTTP $status after ${elapsed}s"
      exit 0
    fi
  fi
  sleep "$interval"
  elapsed=$(( elapsed + interval ))
done

echo "wait-for-ready: $url did not respond as expected within ${max_wait}s (last status: ${status:-none}, expected: ${expected_status:-any})" >&2
exit 1
