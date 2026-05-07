# v1 #65 edit_get_lr_multiplier_clamp_post_training

## Category

code_editing

## Repo

`autoresearch` - karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Prompt

> Modify the function `get_lr_multiplier` inside the `autoresearch` package so that the behavior contract below holds:
> 
> > The target is the cosine LR-schedule helper `get_lr_multiplier(progress)` declared at module scope inside the `autoresearch` checkout. It returns the learning-rate multiplier as a function of training progress in `[0, 1]`, parameterised by the module-level constants `WARMUP_RATIO`, `WARMDOWN_RATIO`, and `FINAL_LR_FRAC`. For `progress > 1.0` (which can happen if a training loop overshoots the planned step budget), the existing cooldown branch evaluates `(1.0 - progress) / WARMDOWN_RATIO` to a negative number and returns a negative LR multiplier -- a silent bug.
> 
> Behavior contract:
> 
> Modify the function `get_lr_multiplier` (declared at module scope inside `autoresearch`) so that any post-training progress value (`progress >= 1.0`) is clamped to the final learning-rate fraction:
> 
> - Calling `get_lr_multiplier(progress)` with `progress >= 1.0` now returns the module-level constant `FINAL_LR_FRAC` directly. For example, `get_lr_multiplier(1.5)` returns `FINAL_LR_FRAC`, and `get_lr_multiplier(2.0)` returns `FINAL_LR_FRAC`.
> - Existing behaviour on `progress < 1.0` is preserved exactly, including the boundary case `progress == 1.0` which already evaluates to `FINAL_LR_FRAC` via the cooldown branch: `get_lr_multiplier(0.0)` returns `1.0` (the warmup branch when `WARMUP_RATIO` is `0`), `get_lr_multiplier(0.25)` returns `1.0` (the plateau between warmup end and `1.0 - WARMDOWN_RATIO`), `get_lr_multiplier(0.75)` returns `0.5`, and `get_lr_multiplier(1.0)` returns `FINAL_LR_FRAC`.
> 
> The minimal change is a single guard at the very top of the function body (before the warmup branch that consults `WARMUP_RATIO`) that short-circuits to `FINAL_LR_FRAC` when `progress >= 1.0`. Do NOT modify the existing warmup, plateau, or cooldown branches.
> 
> Constraints:
> - Edit exactly ONE file inside `./`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`train.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so `get_lr_multiplier(2.0)` returns a negative LR multiplier from the cooldown branch (`no-change`).
- Adds a guard for `progress > 1.0` (strict inequality) but misses the `progress == 1.0` boundary case, leaving it to the cooldown branch which happens to also return `FINAL_LR_FRAC` -- so this looks fine but a stricter clamp would have caught it; conversely guarding on `progress > 1.0` instead of `>= 1.0` and accidentally changing the cooldown behaviour at the boundary breaks the regression on `progress == 1.0` (`partial-edit`).
- Clamps the progress argument itself (e.g. `progress = min(progress, 1.0)`) so other branches still execute, accidentally returning `1.0 * 1.0 + 0 * FINAL_LR_FRAC = 1.0` for clamped inputs rather than `FINAL_LR_FRAC` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
