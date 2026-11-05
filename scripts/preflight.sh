#!/usr/bin/env bash
set -euo pipefail

uv run pytest
.venv/bin/python -m compileall app tests
git diff --check

if git diff --name-only --diff-filter=ACM | grep -E '(^|/)(\.env|.*\.pem|.*\.key)$'; then
  echo "Potential secret file in diff" >&2
  exit 1
fi

echo "PREFLIGHT PASS"
