#!/usr/bin/env sh
set -eu

API_URL=${API_URL:-${NEXT_PUBLIC_API_URL:-http://localhost:8000}}
WEB_URL=${WEB_URL:-http://localhost:${FRONTEND_PORT:-3000}}
CURL=${CURL:-curl}
TIMEOUT_SECONDS=${TIMEOUT_SECONDS:-10}

API_URL=${API_URL%/}
WEB_URL=${WEB_URL%/}

probe() {
  label=$1
  url=$2
  "$CURL" --fail --silent --show-error --max-time "$TIMEOUT_SECONDS" "$url" >/dev/null
  printf 'OK %-16s %s\n' "$label" "$url"
}

probe "API health" "$API_URL/api/v1/health"
probe "domain registry" "$API_URL/api/v1/domains"
probe "frontend" "$WEB_URL/"

printf '%s\n' "Smoke test passed."
