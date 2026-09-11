#!/usr/bin/env bash
# Single entry point used by README, CI and the pre-push gate.
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-}" in
  install)
    python3 - <<'PY'
import sys
assert sys.version_info >= (3, 9), f"Python >= 3.9 required, found {sys.version.split()[0]}"
print(f"python {sys.version.split()[0]} ok - creality3mf has no third-party dependencies")
PY
    ;;
  example)
    python3 examples/nameplate.py "HELLO" -o examples/out/nameplate.3mf
    python3 creality3mf.py inspect examples/out/nameplate.3mf
    ;;
  test)
    python3 -m unittest discover -s tests -v
    ;;
  *)
    echo "usage: bash scripts/dev.sh {install|example|test}" >&2
    exit 2
    ;;
esac
