#!/bin/bash

for sc in Qwen2.5-7B-Instruct.sh \
MiniMax-M2.5.sh \
Qwen2.5-14B-Instruct.sh \
Qwen3-8B.sh \
Qwen3-14B.sh \
Qwen3-30B-A3B.sh \
Qwen3-32B.sh \
nano_v3.sh; do
    bash "$sc"
done
