#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${APPAM_ENV_FILE:-${SCRIPT_DIR}/appam.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  printf 'APPAM environment file not found: %s\n' "${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

RUNNER="${APPAM_ENV_RUNNER:-mamba}"
CONDA_BASE="$("${RUNNER}" info --base)"
export PATH="${HOME}/.local/bin:${CONDA_BASE}/bin:${PATH}"

exec "${CONDA_BASE}/envs/appam-backend/bin/gunicorn" \
  --config "${REPO_ROOT}/backend/gunicorn.conf.py" \
  --chdir "${REPO_ROOT}/backend" \
  wsgi:app
