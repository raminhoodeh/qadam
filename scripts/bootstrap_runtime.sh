#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CODEX_BUNDLED_PYTHON="${HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

if [[ -x "${CODEX_BUNDLED_PYTHON}" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-$CODEX_BUNDLED_PYTHON}"
elif command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3.12}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "Python is not installed. Install Python 3.12+ first." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit("Qadam durable runtime requires Python 3.12+. Install Python 3.12 and rerun.")
print(f"python_version={sys.version.split()[0]}")
PY

"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

echo "runtime_bootstrap=ok"
