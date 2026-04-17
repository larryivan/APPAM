#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${APPAM_BUILD_LOG_DIR:-${REPO_ROOT}/docker-data/build-logs}"

mkdir -p "${LOG_DIR}"

timestamp="$(date '+%Y%m%d_%H%M%S')"
if [[ $# -eq 0 ]]; then
  set -- tools
fi

target_slug="$(printf '%s-' "$@" | sed 's/-$//; s/[^A-Za-z0-9_.-]/_/g')"
log_file="${LOG_DIR}/build-${target_slug}-${timestamp}.log"

echo "[appam-build] writing build log to ${log_file}"
echo "[appam-build] running: docker compose build --progress=plain $*" | tee -a "${log_file}"

cd "${REPO_ROOT}"

if docker compose build --progress=plain "$@" 2>&1 | tee -a "${log_file}"; then
  echo "[appam-build] build succeeded: ${log_file}" | tee -a "${log_file}"
else
  status="${PIPESTATUS[0]}"
  echo "[appam-build] build failed with exit ${status}: ${log_file}" | tee -a "${log_file}" >&2
  exit "${status}"
fi
