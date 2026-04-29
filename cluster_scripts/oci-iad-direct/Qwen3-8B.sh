#!/bin/bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/lustre/fsw/portfolios/llmservice/users/drekesh/code/opencode-bench}
CONFIG_DIR=${REPO_ROOT}/cluster_configs
cd "${REPO_ROOT}"

MODEL=Qwen3-8B
TP=4
DP=2
CLUSTER=oci-iad-direct
PARTITION=batch_block1,batch_block3,batch_block4
MAX_TOKENS=8000
JOBS=4
TIMEOUT=300
RETRIES=5
OUTPUT_DIR=/lustre/fsw/portfolios/llmservice/users/drekesh/opencode-bench-results

# Optional:
#   DRY_RUN=1 bash cluster_scripts/oci-iad-direct/Qwen3-8B.sh
#   BENCHMARK_ARGS="--benchmark-id 21" bash cluster_scripts/oci-iad-direct/Qwen3-8B.sh
DRY_RUN=${DRY_RUN:-0}
BENCHMARK_ARGS=${BENCHMARK_ARGS:-}

EXTRA_ARGS=()
if [[ "${DRY_RUN}" == "1" ]]; then
  EXTRA_ARGS+=(--dry-run)
fi
if [[ -n "${BENCHMARK_ARGS}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS+=(${BENCHMARK_ARGS})
fi

python "${REPO_ROOT}/run_cluster.py" \
  --retry-on-timeout "${RETRIES}" \
  --timeout "${TIMEOUT}" \
  --cluster "${CLUSTER}" \
  --config-dir "${CONFIG_DIR}" \
  --model "/hf_models/${MODEL}" \
  -j "${JOBS}" \
  --server-gpus 8 \
  --output-dir "${OUTPUT_DIR}" \
  --expname "${MODEL}" \
  --partition "${PARTITION}" \
  --skip-schema-check \
  --max-output-tokens "${MAX_TOKENS}" \
  --server-args "--tensor-parallel-size ${TP} --data-parallel-size ${DP} --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes" \
  "${EXTRA_ARGS[@]}"
