#!/bin/bash
#
# Pilot panel for v1 code-editing samples.
#
# Scope: by default, runs only the samples that have changed since the last
# panel pilot, so we don't redundantly re-run unchanged samples. The last
# panel covered #51-#74; the +6 hard samples (#75-#80) are new this batch
# and need fresh inference. To re-run the entire 30-sample editing panel
# from scratch, replace the inner --id list with --category code_editing.
#
# Concurrency model:
#   - Models loop is sequential (avoids cross-model rate-limit collisions
#     against the shared switchyard / API proxy).
#   - The 3 seeds for a given model run CONCURRENTLY (backgrounded with
#     `&`); a `wait` after the seed loop blocks until all 3 finish before
#     moving to the next model.
#   - Within each seed, run.py uses `-j 5` to run up to 5 samples in
#     parallel via its ThreadPoolExecutor.
#   - Net concurrency per model: 3 seeds x 5 samples = 15 in-flight samples
#     per model. The 5-second stagger between seed launches avoids a
#     thundering herd of opencode CLI startups.
#
# After this finishes:
#
#   python3 scripts/analyze_localization_panel.py --family editing \
#       --exclude-incomplete > analysis/editing_panel_snapshot.txt
#   python3 scripts/analyze_localization_panel.py --family editing \
#       --exclude-incomplete --json > analysis/editing_panel_snapshot.json
#
# Acceptance criteria (see analysis/README.md):
#   - No same-tier pair with Pearson >= 0.85 on the variance-bearing column subset.
#   - For every model, pass-rate(easy) >= pass-rate(medium) >= pass-rate(hard).



# Samples needing fresh inference: the +6 hard samples (#75-#80).
# (#51-#74 already have full panel coverage from the last pilot iteration.)
EDITING_IDS=(75 76 77 78 79 80)

# Build --id flags for run.py.
ID_ARGS=()
for ID in "${EDITING_IDS[@]}"; do
  ID_ARGS+=(--id "$ID")
done

for MODEL in \
  "nvidia-internal/azure/anthropic/claude-opus-4-6" \
  "nvidia/nvidia/nemotron-3-nano-30b-a3b" \
  "nvidia/minimaxai/minimax-m2.5" \
  "nvidia/nvidia/nemotron-3-super-120b-a12b" \
  "nvidia/qwen/qwen3-next-80b-a3b-thinking"; do
  echo "$(date) MODEL: $MODEL  (3 seeds backgrounded, j=5 each)"
  for i in 1 2 3; do
    /opt/homebrew/bin/python3 run.py \
      --version v1 "${ID_ARGS[@]}" \
      --model "$MODEL" -j 5 \
      --timeout 1200 --retry-on-timeout 5 &
    sleep 5
  done
  wait
  echo "$(date) MODEL: $MODEL  done"
done
