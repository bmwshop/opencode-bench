# v1 #12 refactor_cosine_schedule

## Category

tool_schema

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Multi-step refactor of an existing function against a real training codebase. `train.py` defines `get_lr_multiplier(progress)` at line 518 as a trapezoidal schedule controlled by `WARMUP_RATIO`, `WARMDOWN_RATIO`, and `FINAL_LR_FRAC`. This sample adds a `SCHEDULE` constant (default `"trapezoid"`) and extends `get_lr_multiplier` with a cosine branch active when `SCHEDULE == "cosine"`. Tests the multi-step-editing atomic skill (per Ma et al. arXiv:2604.05013): the model must (a) add a new module-level constant in the right neighborhood, (b) modify an existing function to branch on it, (c) preserve the existing trapezoid branch byte-for-byte behaviorally, and (d) use the already-imported `math.cos` to build the cosine decay formula. This is the highest-variance sample on the suite because it exercises goal retention across the three sub-edits and formula-shape correctness.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. Only `train.py` lines 445-447 (existing schedule constants) and the `get_lr_multiplier` body at 518-525 are relevant. `math` is already imported at line 12 — no new imports required.

## Prompt

> In train.py, add a SCHEDULE constant (default "trapezoid") next to the other schedule constants. Modify get_lr_multiplier so that when SCHEDULE == "cosine" it uses a cosine decay from 1.0 to FINAL_LR_FRAC after warmup, and when SCHEDULE == "trapezoid" it keeps the current behavior exactly. Use math.cos; math is already imported.

## Pass criteria (2 checks)

1. `exec_assert` `train.py` — AST-extracts the four schedule constants (`WARMUP_RATIO`, `WARMDOWN_RATIO`, `FINAL_LR_FRAC`, `SCHEDULE`), imports `math` into the namespace, and exec's `get_lr_multiplier` in isolation. Runs four asserts; all must pass for the check to pass, first failure is the reason.

   - **`SCHEDULE == 'trapezoid'`** — the new constant exists with the correct default string literal.
   - **`abs(get_lr_multiplier(0.0) - 1.0) < 1e-9`** — under `setup: "SCHEDULE = 'cosine'"`, the cosine branch starts at `1.0`. Tolerates floating-point noise from any `math.cos`-based formulation.
   - **`abs(get_lr_multiplier(1.0) - 0.0) < 1e-9`** — under cosine, the endpoint equals `FINAL_LR_FRAC` (`0.0` at baseline).
   - **`abs(get_lr_multiplier(0.625) - 0.75) > 0.05`** — cosine-branch liveness probe. At `progress = 0.625` with baseline constants, the trapezoid formula gives exactly `0.75`. This assert requires the cosine-branch value to deviate from that baseline by more than `0.05` — i.e., the branch must have been added *and* be actually reached at call time. The probe is deliberately loose because the prompt ("cosine decay from 1.0 to FINAL_LR_FRAC *after warmup*") is genuinely ambiguous with `WARMUP_RATIO = 0`: it admits both the **full-range** reading (`t = progress`, giving `lrm(0.625) ≈ 0.309`, diff `0.441`) and the **cooldown-scoped** reading (cosine replaces the trapezoid's linear cooldown, giving `lrm(0.625) ≈ 0.854`, diff `0.104`). Both clear the `0.05` threshold. A model that added `SCHEDULE = "trapezoid"` without wiring a cosine branch falls through to the trapezoid code and returns exactly `0.75`, failing this assert.

2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

### Why behavior probes work here

`get_lr_multiplier` uses only arithmetic on `WARMUP_RATIO`, `WARMDOWN_RATIO`, `FINAL_LR_FRAC`, `SCHEDULE`, and `math.{cos,pi}`. All four constants are AST-extractable via `ast.literal_eval` on the top-level `Assign` nodes, and `math` is a stdlib import seeded into the namespace before the function is exec'd. No user-controlled code from the rest of `train.py` (torch, flash-attn, the dataloader, the training loop) is ever touched.

Behavior probes also tolerate mathematically equivalent rewrites that a text-shape check would reject. The canonical cosine form `FINAL_LR_FRAC + 0.5 * (1.0 - FINAL_LR_FRAC) * (1.0 + math.cos(math.pi * t))` and its commuted variants all evaluate identically at the probe points.

### Residual ceiling

Two failure classes remain uncovered:

- **Trapezoid-branch mutation under `SCHEDULE == "trapezoid"`** — the prompt explicitly requires the model to preserve current trapezoid behavior when `SCHEDULE == "trapezoid"`. The current four asserts only probe the trapezoid branch once (`SCHEDULE == 'trapezoid'` as a literal). A model that subtly alters the trapezoid math while adding the cosine branch would not be caught. Closing this would require 2-3 additional asserts under default `SCHEDULE` probing `lrm(0.25) == 1.0`, `lrm(0.75) == 0.5`, `lrm(1.0) == 0.0`.
- **Cosine decay respecting `FINAL_LR_FRAC` when `FINAL_LR_FRAC != 0`** — the current endpoint assert `lrm(1.0) == 0.0` only verifies the cosine branch against the baseline `FINAL_LR_FRAC = 0`. A model that hardcoded the endpoint to `0` instead of using `FINAL_LR_FRAC` would pass. Closing this would require an additional assert with `setup: "FINAL_LR_FRAC = 0.5"` probing `lrm(1.0) == 0.5`.

## Shortest path

**2-3 tool calls**: `read train.py` → `edit` (add `SCHEDULE` constant and restructure `get_lr_multiplier`) → optional second `edit` if split. Delegation to a subagent for the read half is permitted; recursive tool check accommodates this.

## Fail modes

- Missing `SCHEDULE` constant or wrong default — `exec_assert` fails at `constant 'SCHEDULE' not found` (harness-level) or `assert failed: SCHEDULE == 'trapezoid'` (wrong default).
- Cosine branch never activates (model didn't add a `SCHEDULE == "cosine"` branch, or wired it behind an always-false condition) — under `SCHEDULE = 'cosine'` the function falls through to the trapezoid code, so `lrm(0.625)` returns exactly `0.75`, failing assert 4 (`|0.75 - 0.75| = 0.0` is not `> 0.05`).
- Cosine called with wrong argument shape (e.g. `math.cos(progress)` without `math.pi *`) — under baseline `FINAL_LR_FRAC = 0`, the endpoint `lrm(1.0)` becomes `cos(1) ≈ 0.540`-derived rather than `0`, failing assert 3.
- Cosine direction flipped (endpoints swapped, e.g. the formula reaches `1.0` at `progress = 1.0` instead of `FINAL_LR_FRAC`) — assert 3 fails cleanly.
- Model never modified the file — `exec_assert` fails at `constant 'SCHEDULE' not found` because the baseline has no `SCHEDULE`.
- `SCHEDULE` constant assigned to a non-literal expression (e.g. `SCHEDULE = os.environ.get("SCHED", "trapezoid")`) — harness fails at `constant 'SCHEDULE' not a literal: ...`.
- Function syntax broken by the edit — `ast.parse` reports `SyntaxError at line N: ...`.
- Model deleted or renamed `get_lr_multiplier` — harness reports `function 'get_lr_multiplier' not found`.
- Interpolation endpoint hardcoded to `0` instead of `FINAL_LR_FRAC` — **not caught**; see residual ceiling.
- Trapezoid branch mutated when `SCHEDULE == "trapezoid"` — **not caught**; see residual ceiling.
- Infinite loop inside the cosine branch (pathological) — the per-check 5s `timeout` fires: `exec_assert timeout after 5s`.
- Malformed tool args on whatever path was taken — `call_schema_valid` fails.
