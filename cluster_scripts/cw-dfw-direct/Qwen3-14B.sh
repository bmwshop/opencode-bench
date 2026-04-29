#!/bin/bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)

MODEL=Qwen3-14B
TP=8
CLUSTER=cw-dfw-direct
PARTITION=batch_short
MAX_TOKENS=8000
JOBS=8
TIMEOUT=300
RETRIES=5
OUTPUT_DIR=/lustre/fsw/portfolios/llmservice/users/$USER/opencode-bench-results

python "${REPO_ROOT}/run_cluster.py"  \
--retry-on-timeout ${RETRIES} \
--timeout ${TIMEOUT} \
--cluster ${CLUSTER} \
--model /hf_models/${MODEL} \
-j ${JOBS} \
--server-gpus 8 \
--output-dir ${OUTPUT_DIR} \
--expname ${MODEL} \
--partition ${PARTITION} \
--skip-schema-check \
--max-output-tokens ${MAX_TOKENS} \
--server-args "--tensor-parallel-size ${TP} --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
