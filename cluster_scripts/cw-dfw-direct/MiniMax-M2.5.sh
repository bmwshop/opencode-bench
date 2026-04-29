#!/bin/bash
MODEL=MiniMax-M2.5
TP=8
CLUSTER=cw-dfw-direct
PARTITION=batch_short
JOBS=8
TIMEOUT=300
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
--server-args "--tensor-parallel-size ${TP} --trust-remote-code --enable_expert_parallel --enable-auto-tool-choice --tool-call-parser minimax_m2 --reasoning-parser minimax_m2_append_think"
