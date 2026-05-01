#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
CONFIG_DIR=${REPO_ROOT}/cluster_configs
cd "${REPO_ROOT}"

CLUSTER=${CLUSTER:-cw-dfw-direct}
PARTITION=${PARTITION:-batch_short}

RUN_NAME=${RUN_NAME:-combined-v1-2-dfw_qwen3_32b_msg_fmt_lr1e-05_ep1.0_gbs32}
SOURCE_ROOT=${SOURCE_ROOT:-/lustre/fsw/portfolios/llmservice/users/smajumdar/results/opencode_paper/v1}
OUTPUT_ROOT=${OUTPUT_ROOT:-/lustre/fsw/portfolios/llmservice/users/${USER}/opencode-bench-results}
MODEL_MOUNT="${SOURCE_ROOT}:${SOURCE_ROOT}"

MAX_TOKENS=8192
JOBS=4
TIMEOUT=600
RETRIES=5
TRIALS=${TRIALS:-3}
SERVER_ARGS="--tensor-parallel-size 8 --data-parallel-size 1 --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"

# Optional:
#   DRY_RUN=1 bash cluster_scripts/cw-dfw-direct/run_selected_sft.sh
#   BENCHMARK_ARGS="--benchmark-id 21" bash cluster_scripts/cw-dfw-direct/run_selected_sft.sh
DRY_RUN=${DRY_RUN:-0}
BENCHMARK_ARGS=${BENCHMARK_ARGS:-}

COMMON_ARGS=()
if [[ "${DRY_RUN}" == "1" ]]; then
  COMMON_ARGS+=(--dry-run)
fi
if [[ -n "${BENCHMARK_ARGS}" ]]; then
  # shellcheck disable=SC2206
  COMMON_ARGS+=(${BENCHMARK_ARGS})
fi

if [[ ! -d "${SOURCE_ROOT}" ]]; then
  echo "ERROR: SOURCE_ROOT does not exist: ${SOURCE_ROOT}" >&2
  exit 1
fi

MODEL_DIR="${SOURCE_ROOT}/${RUN_NAME}/final_hf_model"
if [[ ! -d "${MODEL_DIR}" ]]; then
  echo "ERROR: missing checkpoint: ${MODEL_DIR}" >&2
  echo "       Set SOURCE_ROOT or RUN_NAME if this checkpoint lives in another results tree." >&2
  exit 1
fi

OUTPUT_DIR="${OUTPUT_ROOT}/${RUN_NAME}/opencode-bench-eval/"
mkdir -p "${OUTPUT_DIR}"

for trial in $(seq 1 "${TRIALS}"); do
  expname=$(printf "eval-%02d" "${trial}")

  echo "=== submitting ${RUN_NAME} ${expname}/${TRIALS} on ${CLUSTER} ==="
  echo "    model:  ${MODEL_DIR}/"
  echo "    output: ${OUTPUT_DIR}${expname}"

  python "${REPO_ROOT}/run_cluster.py" \
    --cluster "${CLUSTER}" \
    --config-dir "${CONFIG_DIR}" \
    --expname "${expname}" \
    --model "${MODEL_DIR}" \
    --mount-paths "${MODEL_MOUNT}" \
    --server-nodes 1 \
    --server-gpus 8 \
    --timeout "${TIMEOUT}" \
    --output-dir "${OUTPUT_DIR}" \
    --server-args "${SERVER_ARGS}" \
    --time-min "01:45:00" \
    -j "${JOBS}" \
    --retry-on-timeout "${RETRIES}" \
    --dependent-jobs 0 \
    --max-output-tokens "${MAX_TOKENS}" \
    --reuse-code \
    --skip-schema-check \
    --partition "${PARTITION}" \
    "${COMMON_ARGS[@]}"
done
