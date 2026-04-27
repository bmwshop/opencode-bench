#!/bin/bash
# Code-review pilot launcher (paper-faithful PR-judgment, Ma et al. arXiv:2604.05013).
#
# Runs the 5-model x 3-seed panel for the v1 code_review category (#91-#100).
# Each invocation runs the entire category at -j 5 (5 samples in parallel).
# Total: 5 models * 3 seeds = 15 outer invocations.
#
# The samples have agent=plan in the row, so run.py automatically launches
# opencode with --agent plan (read-only). The agent receives a PR diff +
# issue and emits <judgment>YES|NO</judgment> + <review>...</review>.
#
# Healthy-pattern criteria (per the plan):
#   - claude / super pass >=7/10 samples on majority of seeds (solvable)
#   - at least one weaker model passes >=3/10 (not impossibly hard)
#   - no sample is 0/15 across all model+seeds (label likely wrong)
#   - no sample is 15/15 (too easy; issue text too explicit)
#
# After running: aggregate with `eval.py --version v1 --category code_review`.
# If any sample fails healthy-pattern criteria, iterate the ISSUE_TEXT only
# (never the truth table, reference edit, or label) and re-pilot only the
# iterated sample. Cap at 2 iterations per sample.

set -e

MODELS=(
  "nvidia-internal/azure/anthropic/claude-opus-4-6"
  "nvidia/nvidia/nemotron-3-nano-30b-a3b"
  "nvidia/minimaxai/minimax-m2.5"
  "nvidia/nvidia/nemotron-3-super-120b-a12b"
  "nvidia/qwen/qwen3-next-80b-a3b-thinking"
)

for MODEL in "${MODELS[@]}"; do
  for i in 1 2 3; do
    echo "=== model=$MODEL seed=$i (category=code_review, -j 5) ==="
    /opt/homebrew/bin/python3 run.py \
      --version v1 --category code_review \
      --model "$MODEL" \
      -j 5 \
      --timeout 1200 --retry-on-timeout 5
  done
done

echo
echo "Pilot complete. Aggregate with:"
echo "  python3 eval.py --version v1 --category code_review"
