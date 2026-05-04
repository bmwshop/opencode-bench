#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
CONFIG_DIR=${REPO_ROOT}/cluster_configs

MODEL="sft-all_0502.final_alex"
ITER="iter_0000300"
BASE_DIR="/lustre/fsw/portfolios/llmservice/users/drekesh/results/sft/${MODEL}"
CKPT="${BASE_DIR}/checkpoints/${ITER}/evals/hf/hf"
MODEL_MOUNT="${BASE_DIR}:${BASE_DIR}"
TP=8
CLUSTER=cw-dfw-direct
PARTITION=interactive
TIME_MIN=01:00:00
JOBS=4
TIMEOUT=450
RETRIES=5
OUTPUT_DIR="/lustre/fsw/portfolios/llmservice/users/${USER}/opencode-bench-results"
EXPNAME="${MODEL}-${ITER}-no-cleanup"

if [[ ! -d "${CKPT}" ]]; then
    echo "ERROR: missing checkpoint: ${CKPT}" >&2
    exit 1
fi

python "${REPO_ROOT}/run_cluster.py" \
    --retry-on-timeout "${RETRIES}" \
    --timeout "${TIMEOUT}" \
    --cluster "${CLUSTER}" \
    --config-dir "${CONFIG_DIR}" \
    --model "${CKPT}" \
    --mount-paths "${MODEL_MOUNT}" \
    -j "${JOBS}" \
    --server-gpus 8 \
    --output-dir "${OUTPUT_DIR}" \
    --expname "${EXPNAME}" \
    --partition "${PARTITION}" \
    --time-min "${TIME_MIN}" \
    --skip-schema-check \
    --no-cleanup-projects \
    --server-args "--tensor-parallel-size ${TP} --gpu-memory-utilization 0.8 --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser deepseek_r1 --mamba_ssm_cache_dtype float32"
