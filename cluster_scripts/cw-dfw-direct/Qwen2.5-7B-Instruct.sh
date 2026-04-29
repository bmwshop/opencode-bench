#!/bin/bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
CONFIG_DIR=${REPO_ROOT}/cluster_configs

MODEL=Qwen2.5-7B-Instruct
TP=4
PP=2
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
--config-dir ${CONFIG_DIR} \
--model /hf_models/${MODEL} \
-j ${JOBS} \
--server-gpus 8 \
--output-dir ${OUTPUT_DIR} \
--expname ${MODEL} \
--partition ${PARTITION} \
--skip-schema-check \
--max-output-tokens ${MAX_TOKENS} \
--server-args "--tensor-parallel-size ${TP} --pipeline-parallel-size ${PP} --enable-auto-tool-choice --tool-call-parser hermes"
