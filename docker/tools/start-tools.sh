#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data /workspaces/projects /databases

OPENCODE_PORT="${OPENCODE_PORT:-19455}"
OPENCODE_BASE_URL="${OPENCODE_BASE_URL:-http://127.0.0.1:${OPENCODE_PORT}}"
APPAM_DB_PATH="${APPAM_DB_PATH:-/data/app_database.db}"
export OPENCODE_BASE_URL

mkdir -p "$(dirname "${APPAM_DB_PATH}")"

if [[ -n "${APPAM_PALEO_MAXQUANT_CMD:-}" && ! -f "${APPAM_PALEO_MAXQUANT_CMD}" ]]; then
  echo "[appam-tools] Warning: APPAM_PALEO_MAXQUANT_CMD points to a missing file: ${APPAM_PALEO_MAXQUANT_CMD}" >&2
fi

if command -v opencode >/dev/null 2>&1; then
  echo "[appam-tools] Starting OpenCode API on 0.0.0.0:${OPENCODE_PORT}" >&2
  opencode serve --hostname 0.0.0.0 --port "${OPENCODE_PORT}" --print-logs &
  OPENCODE_PID=$!
else
  echo "[appam-tools] Warning: opencode command not found; OpenCode API will be unavailable." >&2
  OPENCODE_PID=""
fi

cleanup() {
  local status=0
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill -TERM "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${OPENCODE_PID:-}" ]]; then
    kill -TERM "${OPENCODE_PID}" 2>/dev/null || true
  fi
  wait "${BACKEND_PID:-}" 2>/dev/null || status=$?
  wait "${OPENCODE_PID:-}" 2>/dev/null || true
  exit "${status}"
}

trap cleanup INT TERM

micromamba run -n backend python /opt/appam/backend/run.py &
BACKEND_PID=$!

wait "${BACKEND_PID}"
