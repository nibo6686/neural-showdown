#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH="$(pwd)/trainer/src"
export NEURAL_SIM_CORE_CWD="$(pwd)/sim-core"

SERVER_JS="$(pwd)/sim-core/dist/src/server.js"

if [ ! -f "$SERVER_JS" ]; then
  echo "sim-core build not found. Installing/building sim-core..."
  npm --prefix sim-core install
  npm --prefix sim-core run build
fi

export NEURAL_SIM_CORE_COMMAND_JSON="[\"node\",\"$SERVER_JS\"]"

export NEURAL_ROLLOUTS_PER_ACTION="${NEURAL_ROLLOUTS_PER_ACTION:-8}"
export NEURAL_ROLLOUT_MODE="${NEURAL_ROLLOUT_MODE:-auto}"

# V1 balanced defaults
export NEURAL_ROLLOUT_WEIGHT="${NEURAL_ROLLOUT_WEIGHT:-0.55}"
export NEURAL_RANKER_WEIGHT="${NEURAL_RANKER_WEIGHT:-0.40}"
export NEURAL_POLICY_WEIGHT="${NEURAL_POLICY_WEIGHT:-0.05}"

python -m neural.live_eval_healthcheck
python -m neural.live_eval_server
