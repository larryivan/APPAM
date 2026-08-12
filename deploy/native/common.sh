#!/usr/bin/env bash

resolve_environment_base() {
  local runner="$1"

  "${runner}" info --json | python3 -c '
import json
import sys

data = json.load(sys.stdin)
base = data.get("base environment") or data.get("root_prefix") or data.get("base_environment")
if not isinstance(base, str) or not base.strip():
    raise SystemExit("Environment runner did not report its base directory.")
print(base.strip())
'
}
