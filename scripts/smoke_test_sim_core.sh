#!/usr/bin/env bash
set -euo pipefail

# Non-network launch smoke test. It exercises the existing Python -> Node
# NDJSON boundary through the repository's existing parity test inputs.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
SIM_CORE_DIR="$REPO_ROOT/sim-core"
SERVER_JS="$SIM_CORE_DIR/dist/src/server.js"

PYTHON_BIN="${PYTHON_BIN:-python3}"
NODE_BIN="${NODE_BIN:-node}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  exit 127
fi
if ! command -v "$NODE_BIN" >/dev/null 2>&1; then
  echo "Node executable not found: $NODE_BIN" >&2
  exit 127
fi
if [ ! -f "$SERVER_JS" ]; then
  echo "sim-core build not found: $SERVER_JS" >&2
  echo "Build it explicitly with npm run build --prefix sim-core." >&2
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/trainer/src${PYTHONPATH:+:$PYTHONPATH}"
export NEURAL_SIM_CORE_CWD="$SIM_CORE_DIR"
export NEURAL_SIM_CORE_COMMAND_JSON="$(NEURAL_NODE_BIN="$NODE_BIN" "$PYTHON_BIN" -c 'import json, os; print(json.dumps([os.environ["NEURAL_NODE_BIN"], "dist/src/server.js"]))')"

cd "$REPO_ROOT"
exec "$PYTHON_BIN" -m pytest trainer/tests/test_sim_core_parity.py -q -m 'not replay'
