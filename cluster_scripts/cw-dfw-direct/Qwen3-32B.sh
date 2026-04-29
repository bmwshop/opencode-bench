#!/bin/bash
MODEL=Qwen3-32B
TP=8
DP=1
CLUSTER=cw-dfw-direct
PARTITION=batch_short
MAX_TOKENS=8000
JOBS=4
TIMEOUT=450
RETRIES=5
OUTPUT_DIR=/lustre/fsw/portfolios/llmservice/users/$USER/opencode-bench-results


python run_cluster.py  \
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
--server-args "--tensor-parallel-size ${TP} --data-parallel-size ${DP} --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
