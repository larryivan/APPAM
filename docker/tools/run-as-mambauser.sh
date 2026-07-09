#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  mkdir -p /data /workspaces/projects /runtime-logs
  chown mambauser:mambauser /data /workspaces /workspaces/projects /runtime-logs
  chown -R mambauser:mambauser /data /runtime-logs
  if [[ "${APPAM_FIX_PROJECT_OWNERSHIP:-false}" =~ ^(1|true|yes|on)$ ]]; then
    chown -R mambauser:mambauser /workspaces/projects
  fi
  exec gosu mambauser "$@"
fi

exec "$@"
