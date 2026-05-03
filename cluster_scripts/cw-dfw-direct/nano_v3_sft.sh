#!/bin/bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
CONFIG_DIR=${REPO_ROOT}/cluster_configs

MODEL="sft-all_0417.final.alex"
MODEL="sft-all_0502.final_alex"
MODEL="sft-all_0502b.final_alex"
STEPS="100 200 300 400 500 600"
BASE_DIR=/lustre/fsw/portfolios/llmservice/users/drekesh/results/sft/${MODEL}
MODEL_MOUNT=${BASE_DIR}:${BASE_DIR}
TP=8
CLUSTER=cw-dfw-direct
PARTITION=batch_short
JOBS=4
NEVALS=4
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
--mount-paths ${MODEL_MOUNT} \
-j ${JOBS} \
--server-gpus 8 \
--output-dir ${OUTPUT_DIR} \
--expname ${MODEL}-${ITER} \
--parallel-jobs=${NEVALS} \
--partition ${PARTITION} \
--skip-schema-check \
--server-args "--tensor-parallel-size ${TP} --gpu-memory-utilization 0.8 --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser deepseek_r1 --mamba_ssm_cache_dtype float32"
done
