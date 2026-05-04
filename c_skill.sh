#!/bin/bash
#
# Pilot panel for v1 SKILL family samples (#401-#410).
#
# Scope: all 10 currently-authored skill samples need fresh inference (no
# traces on disk yet). Once the family grows past 10, swap the explicit
# --id list below for `--category skill` to auto-include any new entries
# that landed in samples_v1.jsonl.
#
# Tier coverage in the current 10:
#   #401-#403  Tier A workflow      (review-flow / audit-flow / summary-flow)
#   #404-#406  Tier A style-rules   (naming / api-style / encoding)
#   #407-#409  Tier A code-backed   (validate / checksum / count-imports)
#   #410       Tier B discovery    (2-skill workspace; correct one chosen)
#
# Concurrency model: identical to c_editing.sh.
#   - Models loop sequentially (avoids cross-model rate-limit collisions
#     against the shared switchyard / API proxy).
#   - 3 seeds per model run CONCURRENTLY (backgrounded with `&`); `wait`
#     blocks until all 3 finish before moving to the next model.
#   - Within each seed, run.py uses `-j 5` to run up to 5 samples in
#     parallel via its ThreadPoolExecutor.
#   - Net concurrency per model: 3 seeds x 5 samples = 15 in-flight
#     samples per model. The 5-second stagger avoids a thundering herd
#     of opencode CLI startups.
#
# Trial count: 10 samples x 5 models x 3 seeds = 150 trials. Estimated
# wall time ~30-60 minutes depending on slowest seed.
#
# Per-trial timeout: 900s (was 600s in the first pilot). The previous
# 600s budget caused minimax-m2.5 to drop 3 of 15 workflow trials
# (#401-#403 timed out). Workflow samples include `read` calls that can
# return very large file contents (e.g. requests/utils.py at the pinned
# commit is ~1k lines), and minimax burns more turns deliberating before
# committing to a write. 900s gives sufficient headroom; trim back if
# claude/super finish much faster.
#
# After this finishes:
#
#   # Analyzer support for --family skill is not yet wired into
#   # data/scripts/analyze_localization_panel.py. Until then, use eval.py
#   # directly to score and inspect:
#
#   python3 eval.py --version v1 --category skill --format text \
#     | tee analysis/skill_panel_raw.txt
#
#   # Per-sample pass-rate breakdown across the most recent 3 runs per
#   # model can be read from each run-dir's scores.json. A
#   # `data/scripts/analyze_localization_panel.py --family skill` extension
#   # is on the v1 SKILL plan (phase 6).
#
# Single-sample dev test (skip the model x seed grid; useful for spot-
# checking a sample after editing its SKILL.md fixture):
#
#   /opt/homebrew/bin/python3 run.py --version v1 --id 401 \
#     --model nvidia-internal/azure/anthropic/claude-opus-4-6 \
#     --timeout 600

# Skill samples to run. Update this list (or replace with --category skill)
# when new skill samples are authored.
#
# Tier coverage:
#   #401-#403  Tier A workflow         (review-flow / audit-flow / summary-flow)
#   #404-#406  Tier A style-rules      (naming / api-style / encoding)
#   #407-#409  Tier A code-backed      (validate / checksum / count-imports)
#   #410-#414  Tier B discovery        (2-skill / 3-skill / opaque / overlapping / no-match)
#   #415-#422  Tier C SKILL-vs-prompt  (sister samples for #301-#308; recipe lives in SKILL.md)
#   #423-#426  Tier D selectivity     (5-skill pool / no-match-plausible / language / vocab-pollution)
#   #427-#430  Tier E composition     (sequential / independent / prose-chain / 3-skill)
SKILL_IDS=(401 402 403 404 405 406 407 408 409 410 411 412 413 414 415 416 417 418 419 420 421 422 423 424 425 426 427 428 429 430)
SKILL_IDS=(415 416 417 418 419 420 421 422)

ID_ARGS=()
for ID in "${SKILL_IDS[@]}"; do
  ID_ARGS+=(--id "$ID")
done

#   "nvidia-internal/azure/anthropic/claude-opus-4-6" \
#   "nvidia/nvidia/nemotron-3-nano-30b-a3b" \
#   "nvidia/minimaxai/minimax-m2.5" \
#   "nvidia/nvidia/nemotron-3-super-120b-a12b" \

for MODEL in \
  "nvidia/nvidia/nemotron-3-super-120b-a12b" \
  "nvidia/qwen/qwen3-next-80b-a3b-thinking"; do
  echo "$(date) MODEL: $MODEL  (3 seeds backgrounded, j=5 each)"
  for i in 1 2 3; do
    /opt/homebrew/bin/python3 run.py \
      --workspace . \
      --version v1 "${ID_ARGS[@]}" \
      --model "$MODEL" -j 1 \
      --timeout 900 --retry-on-timeout 3 &
    sleep 5
  done
  wait
  echo "$(date) MODEL: $MODEL  done"
done
