#!/usr/bin/env bash
# NV-SynthForge — Track C (SDG + OCR) demo launcher.
#
# Starts the offline FastAPI backend on the first free port among 8000/8001/8002
# and the Next.js frontend on 3000, wired to that backend via
# BACKEND_INTERNAL_URL (server rewrites) and NEXT_PUBLIC_API_URL (browser).
#
# Windows-friendly: run from Git Bash. Ctrl-C stops both services.
#   scripts/demo-track-c.sh
#
# Overrides: BACKEND_PORTS="8000 8001 8002"  FRONTEND_PORT=3000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
HOST="127.0.0.1"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
read -r -a CANDIDATE_PORTS <<<"${BACKEND_PORTS:-8000 8001 8002}"
LOG_DIR="$ROOT/.demo-logs"
mkdir -p "$LOG_DIR"

# Small Python interpreter used only for the port probe and health wait.
PYBIN="python"
command -v "$PYBIN" >/dev/null 2>&1 || PYBIN="py"

port_free() {
  "$PYBIN" - "$1" <<'PY'
import socket, sys
s = socket.socket()
free = s.connect_ex(("127.0.0.1", int(sys.argv[1]))) != 0
s.close()
sys.exit(0 if free else 1)
PY
}

BACKEND_PORT=""
for candidate in "${CANDIDATE_PORTS[@]}"; do
  if port_free "$candidate"; then
    BACKEND_PORT="$candidate"
    break
  fi
  echo "Port $candidate is busy, trying the next candidate..." >&2
done
if [ -z "$BACKEND_PORT" ]; then
  echo "No free backend port among ${CANDIDATE_PORTS[*]}." >&2
  exit 1
fi
BACKEND_URL="http://$HOST:$BACKEND_PORT"

# Prefer the project venv so cleanup targets uvicorn directly (not a uv wrapper).
if [ -x "$BACKEND_DIR/.venv/Scripts/python.exe" ]; then
  BACKEND_PY="$BACKEND_DIR/.venv/Scripts/python.exe"
elif [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  BACKEND_PY="$BACKEND_DIR/.venv/bin/python"
else
  BACKEND_PY=""
fi

PIDS=()
cleanup() {
  trap - INT TERM EXIT
  echo ""
  echo "Stopping demo services..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup INT TERM EXIT

echo "==> Backend  $BACKEND_URL   (logs: $LOG_DIR/backend.log)"
(
  cd "$BACKEND_DIR"
  if [ -n "$BACKEND_PY" ]; then
    exec "$BACKEND_PY" -m uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT"
  else
    exec uv run uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT"
  fi
) >"$LOG_DIR/backend.log" 2>&1 &
PIDS+=($!)

# Wait (up to ~60s) for the backend health endpoint to answer.
backend_ready=""
for _ in $(seq 1 60); do
  if "$PYBIN" -c "import urllib.request,sys; urllib.request.urlopen('$BACKEND_URL/api/v1/health', timeout=2)" >/dev/null 2>&1; then
    backend_ready="yes"
    break
  fi
  sleep 1
done
if [ -z "$backend_ready" ]; then
  echo "Backend did not become healthy — see $LOG_DIR/backend.log" >&2
  exit 1
fi
echo "==> Backend healthy."

echo "==> Frontend http://$HOST:$FRONTEND_PORT   (logs: $LOG_DIR/frontend.log)"
(
  cd "$FRONTEND_DIR"
  export PORT="$FRONTEND_PORT"
  export BACKEND_INTERNAL_URL="$BACKEND_URL"
  export NEXT_PUBLIC_API_URL="$BACKEND_URL"
  exec pnpm run dev
) >"$LOG_DIR/frontend.log" 2>&1 &
PIDS+=($!)

cat <<EOF

------------------------------------------------------------------
NV-SynthForge — Track C demo is starting.

  Studio    http://$HOST:$FRONTEND_PORT/studio?domain=invoices
  OCR       http://$HOST:$FRONTEND_PORT/ocr
  API docs  $BACKEND_URL/docs

Backend    $BACKEND_URL
Smoke test API_BASE=$BACKEND_URL $PYBIN scripts/ocr-demo-smoke.py

The frontend needs a few seconds to compile on first load.
Press Ctrl-C to stop both services.
------------------------------------------------------------------
EOF

wait
