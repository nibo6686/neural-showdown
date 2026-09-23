#!/usr/bin/env bash
set -euo pipefail

# POSIX launcher for macOS and Linux. Dependencies are intentionally prepared
# by the caller; this script never installs packages or fetches fixtures.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
SIM_CORE_DIR="$REPO_ROOT/sim-core"
SERVER_JS="$SIM_CORE_DIR/dist/src/server.js"

PYTHON_BIN="${PYTHON_BIN:-python3}"
NODE_BIN="${NODE_BIN:-node}"
NPM_BIN="${NPM_BIN:-npm}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN to a supported interpreter, for example python3." >&2
  exit 127
fi
if ! command -v "$NODE_BIN" >/dev/null 2>&1; then
  echo "Node executable not found: $NODE_BIN" >&2
  echo "Set NODE_BIN to the local Node executable." >&2
  exit 127
fi

needs_build=false
if [ ! -f "$SERVER_JS" ]; then
  needs_build=true
elif [ -n "$(find "$SIM_CORE_DIR/src" -type f -newer "$SERVER_JS" -print -quit)" ]; then
  needs_build=true
fi

if [ "$needs_build" = true ]; then
  if [ ! -d "$SIM_CORE_DIR/node_modules" ]; then
    echo "sim-core dependencies are missing: $SIM_CORE_DIR/node_modules" >&2
    echo "Run npm ci --prefix sim-core, then rerun this launcher." >&2
    exit 1
  fi
  if ! command -v "$NPM_BIN" >/dev/null 2>&1; then
    echo "npm executable not found: $NPM_BIN" >&2
    echo "Set NPM_BIN to the local npm executable." >&2
    exit 127
  fi
  echo "sim-core build not found; building with the existing local dependencies..." >&2
  "$NPM_BIN" --prefix "$SIM_CORE_DIR" run build
fi

if [ ! -f "$SERVER_JS" ]; then
  echo "sim-core build did not produce $SERVER_JS" >&2
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/trainer/src${PYTHONPATH:+:$PYTHONPATH}"
export NEURAL_SIM_CORE_CWD="$SIM_CORE_DIR"
export NEURAL_SIM_CORE_COMMAND_JSON="$(NEURAL_NODE_BIN="$NODE_BIN" "$PYTHON_BIN" -c 'import json, os; print(json.dumps([os.environ["NEURAL_NODE_BIN"], "dist/src/server.js"]))')"

# Preserve live defaults from Python. Callers may still override them via the
# documented NEURAL_* environment variables before invoking this script.
"$PYTHON_BIN" -m neural.live_eval_healthcheck
exec "$PYTHON_BIN" -m neural.live_eval_server
