#!/bin/bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
CONFIG_DIR=${REPO_ROOT}/cluster_configs

MODEL="sft-all_0417.final.alex"
STEPS="100 200 300"
BASE_DIR=/lustre/fsw/portfolios/llmservice/users/drekesh/results/sft/${MODEL}
TP=8
CLUSTER=cw-dfw-direct
PARTITION=batch_short
JOBS=4
TIMEOUT=450
RETRIES=5
OUTPUT_DIR=/lustre/fsw/portfolios/llmservice/users/$USER/opencode-bench-results

for STEP in ${STEPS}; do
ITER=$(printf "iter_%07d" "${STEP}")
CKPT="${BASE_DIR}/checkpoints/${ITER}/evals/hf/hf"

python "${REPO_ROOT}/run_cluster.py"  \
--retry-on-timeout ${RETRIES} \
--timeout ${TIMEOUT} \
--cluster ${CLUSTER} \
--config-dir ${CONFIG_DIR} \
--model ${CKPT} \
-j ${JOBS} \
--server-gpus 8 \
--output-dir ${OUTPUT_DIR} \
--expname ${MODEL}-${ITER} \
--partition ${PARTITION} \
--skip-schema-check \
--server-args "--tensor-parallel-size ${TP} --gpu-memory-utilization 0.8 --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser deepseek_r1 --mamba_ssm_cache_dtype float32"
done
