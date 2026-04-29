#!/bin/bash
MODEL=NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
TP=8
CLUSTER=cw-dfw-direct
PARTITION=batch_short
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
--server-args "--tensor-parallel-size ${TP} --gpu-memory-utilization 0.8 --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser deepseek_r1 --mamba_ssm_cache_dtype float32"
