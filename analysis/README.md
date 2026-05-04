# Panel analysis (localization + editing + mutants + orchestration)

Artifacts produced by
[`data/scripts/analyze_localization_panel.py`](../data/scripts/analyze_localization_panel.py).
The same script analyses four v1 sample families via `--family`:

- `--family localization` (default) — structured-output samples #21–#50,
  manifest `data/v1_localization_criteria.json`, category `code_localization`.
- `--family editing` — de-leaked code-editing samples #51–#80, manifest
  `data/v1_editing_criteria.json`, category `code_editing`.
- `--family mutants` — tool-restriction mutants #201–#230, manifest
  `data/v1_mutant_criteria.json`, category `tool_restriction`. Each
  mutant pairs a v1 substantive parent (editing/localization/review) with
  a per-tool restriction delivered through `opencode.json` permissions,
  AGENTS.md instructions, or a custom main agent persona file.
- `--family orchestration` — prescriptive orchestration samples #301–#310,
  manifest `data/v1_orchestration_criteria.json`, category `orchestration`.
  Five graph patterns × two samples each (parallel_dispatch, chain,
  dag_join, iteration, merge). The prompt prescribes the multi-step
  execution graph; verifiers check the model emitted the prescribed shape
  AND produced a correct artifact.

## Files

- `panel_snapshot.json` / `panel_snapshot.txt` — most recent localization
  diversity / gradient snapshot across `runs/v1/*/*`.
- `editing_panel_snapshot.json` / `editing_panel_snapshot.txt` — most
  recent code-editing diversity / gradient snapshot.
  - `n_trials`, `coverage_per_sample` — tells you how complete the pilot is.
  - `matrix` — Pearson correlation between every pair of samples on their
    binary pass/fail vectors (concatenated across model × seed columns that
    are in common across *all* samples in the slice).
  - `same_tier_clone_flags` — any same-tier pair with Pearson ≥ 0.85.
  - `per_model_tier_rates` — the per-model pass-rate-by-tier table used for
    the monotonicity check.
  - `gradient_violations` — lists `(model, higher_tier, lower_tier)` cases
    where the pass rate inverts (i.e. the "easier" tier has a lower
    pass-rate than the "harder" one).

## Pilot status (editing)

The editing snapshot in this directory currently reports `n_trials = 0`
because the de-leak rewrite invalidated all pre-existing #51–#60 traces.
To populate it, run the panel via the dedicated runner script:

```bash
bash c_editing.sh
```

This mirrors `c.sh` but iterates over IDs 51..60. After it finishes,
re-run the analyzer commands at the bottom of this file to refresh
`analysis/editing_panel_snapshot.{txt,json}`. Use `--exclude-incomplete`
in the meantime so partial coverage from in-flight runs doesn't pollute
the gradient denominator with timeouts and trace-not-found entries.

## Acceptance criteria

The same two criteria apply to both families:

- No same-tier pair with Pearson ≥ 0.85 on the variance-bearing column subset.
- For every model, pass-rate(easy) ≥ pass-rate(medium) ≥ pass-rate(hard).

The localization panel uses a 10/10/10 easy/medium/hard split across
#21–#50; the editing panel uses a 3/4/3 split across #51–#60 (planned
9/12/9 across #51–#80 once httpx samples land). The gradient check is
intentionally per-model — a population-average gradient is allowed to
invert temporarily on small panels, but no single model should ever be
strictly better at the harder tier.

### Saturated-column drop (tier-scoped)

Pearson is computed over **non-saturated** (model, seed) columns only,
and saturation is evaluated **per tier** rather than family-wide. A
model whose pass-rate within the tier being correlated is exactly `0.0`
or exactly `1.0` contributes zero variance to every sample in that
tier — its columns collapse the matrix into a degenerate state where
r=1.0 between any two samples that happen to land identically on the
remaining discriminating columns, even when the samples are
structurally distinct.

Concretely on the editing panel: when correlating two **easy** samples,
claude (18/18 easy → 1.00) and nano (0/18 easy → 0.00) are dropped from
that tier's Pearson computation; only minimax, super, and qwen
contribute. When correlating two **medium** samples, claude (27/27 →
1.00) is dropped but nano (1/27 ≠ 0/N) is kept because it has nonzero
variance on medium. Earlier the saturation gate was family-wide, which
let nano slip through on easy (it was 1/45 family-wide, not exactly
0.0) and produced spurious r=1.0 flags between distinct easy samples.

Disable with `pass_vectors_by_sample(..., drop_saturated_models=False)`
if you want the raw matrix including saturated columns. Pass
`saturation_scope_ids=[...]` to control the scope explicitly; by
default `main()` passes the per-tier id list.

## Interpreting partial coverage

Samples 31–50 were added in the expansion batch and need the full
5 × 3 × 30 panel run before the correlation and gradient checks are
fully trusted. You can still run the analyzer incrementally — it walks
every scored run dir and uses the most recent K trials per
`(model, sample)` — so you'll see the picture fill in as runs land.

Rule of thumb:

- Need ≥ 9 trials per sample before trusting a Pearson flag.
- Need ≥ 3 × (tier size) trials per (model, tier) before trusting a
  gradient violation.

To regenerate the localization snapshot:

```bash
python3 data/scripts/analyze_localization_panel.py --ids 21-50 \
  > analysis/panel_snapshot.txt
python3 data/scripts/analyze_localization_panel.py --ids 21-50 --json \
  > analysis/panel_snapshot.json
```

To regenerate the editing snapshot (after the #51–#60 panel run lands):

```bash
python3 data/scripts/analyze_localization_panel.py --family editing \
  > analysis/editing_panel_snapshot.txt
python3 data/scripts/analyze_localization_panel.py --family editing --json \
  > analysis/editing_panel_snapshot.json
```

To regenerate the mutants snapshot (after `bash c_mutants.sh` lands):

```bash
python3 data/scripts/analyze_localization_panel.py --family mutants \
  --exclude-incomplete > analysis/mutant_panel_snapshot.txt
python3 data/scripts/analyze_localization_panel.py --family mutants \
  --exclude-incomplete --json > analysis/mutant_panel_snapshot.json
```

The mutant snapshot adds three sections beyond the standard tier table:

- **Per-mutant vs parent pass-rate** — the per-(model, mutant) table with
  the parent's pass-rate side-by-side and the `delta = parent - mutant`
  column. Empty `parent=` cells mean the parent sample isn't in the
  same `seeds_per_model` run window as the mutants; run `bash c_parents.sh`
  to refresh parent runs and unblock the deltas.
- **Per-mechanism mean delta** — averages the deltas across all mutants
  belonging to a given mechanism (`system`, `agents_md`, `persona`).
  Cleanly answers "does opencode's permission layer hurt models more or
  less than an AGENTS.md instruction does?".
- **Same-restriction / different-mechanism pairs** — focused comparison
  for #212 (AGENTS.md bash-only) vs #219 (persona bash-only) and #216
  (AGENTS.md subagent-required) vs #220 (persona subagent-required).
  Reading the gap surfaces opencode's persona-file plumbing quality.

## Known opencode behavior gaps surfaced by the mutant pilot

Two findings worth tracking from the first mutant panel pilot
(2026-04-27):

- **`{"write": {"*": "deny"}}` is not enforced.** `#207
  m_locate_cookie_tokens_deny_write_system` shows every model freely
  calls `write` and the file gets created on disk
  (`status=completed, output='Wrote file successfully'`). The same
  `{"<tool>": {"*": "deny"}}` shape DOES enforce read/grep/glob/edit
  (claude passes 3/3 on #204/#206/#208). So the per-tool denial layer
  has a write-specific gap. The mutant verifier correctly catches the
  non-compliance — it shows up as a failure, but the diagnostic story
  is "opencode let the agent through," not "the agent disobeyed."
- **Persona-file delivery requires the right shape.** Initial #219/#220
  used `.opencode/agents/main.md` without `mode: primary` frontmatter
  and without a row-level `agent` field, so opencode ran with the
  default agent and the persona file was dead text (0/30 across all 5
  models). After fixing per the v0 #2 `custom_main_agent` pattern
  (distinctive filename, `mode: primary`, row sets `"agent": "<name>"`),
  the persona-file mechanism actually activates. Re-run with
  `bash c_persona_rerun.sh`.

## Orchestration family — gate-check before the first pilot

The orchestration batch (#301–#310) leans heavily on the
`parallel_dispatch_count` verifier (6 of 10 samples require multiple
`task` calls in a single assistant turn). If opencode silently linearizes
parallel tool dispatches into separate steps, those 6 samples will fail
their `parallel_dispatch_count` check for every model — a methodology
artifact, not a model signal.

Before running `bash c_orchestration.sh`, run the gate-check first:

```bash
bash c_orchestration_gate.sh
python3 eval.py --version v1 --id 301 \
  --model nvidia-internal/azure/anthropic/claude-opus-4-6 --format text
```

Inspect the resulting `301_*.jsonl` trace and confirm 3 `tool_use` events
with `name=task` appear between one `step_start` and the corresponding
`step_finish`. If they're spread across separate steps, drop or relax the
`parallel_dispatch_count` checks on #301/#302/#305/#306/#309/#310 to
plain `tool_call_count` before kicking off the pilot.

To regenerate the orchestration snapshot:

```bash
python3 data/scripts/analyze_localization_panel.py --family orchestration \
  --exclude-incomplete > analysis/orchestration_panel_snapshot.txt
python3 data/scripts/analyze_localization_panel.py --family orchestration \
  --exclude-incomplete --json > analysis/orchestration_panel_snapshot.json
```
