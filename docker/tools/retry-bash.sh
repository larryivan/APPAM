#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: retry-bash.sh '<command>'" >&2
  exit 64
fi

command_string="$1"
max_attempts="${APPAM_BUILD_RETRY_ATTEMPTS:-5}"
delay_seconds="${APPAM_BUILD_RETRY_INITIAL_DELAY:-10}"
attempt=1

while true; do
  start_ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[retry-bash] ${start_ts} starting attempt ${attempt}/${max_attempts}: ${command_string}" >&2

  if bash -o pipefail -lc "${command_string}"; then
    end_ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[retry-bash] ${end_ts} attempt ${attempt}/${max_attempts} succeeded" >&2
    exit 0
  fi

  exit_code=$?
  if (( attempt >= max_attempts )); then
    end_ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[retry-bash] ${end_ts} command failed after ${attempt} attempts (exit ${exit_code}): ${command_string}" >&2
    exit "${exit_code}"
  fi

  end_ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[retry-bash] ${end_ts} attempt ${attempt}/${max_attempts} failed (exit ${exit_code}), retrying in ${delay_seconds}s" >&2
  sleep "${delay_seconds}"
  attempt=$((attempt + 1))
  delay_seconds=$((delay_seconds * 2))
done
