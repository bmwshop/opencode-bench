# v1 #65 edit_get_lr_multiplier_clamp_post_training

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='add-guard', scope_kind='single-file', answer_shape='value-equality', unique_trait='guard-progress-ge-one-keep-cooldown-branch'`

## Repo

`autoresearch` - karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Criterion (mechanical)

- Target function (primary): `get_lr_multiplier` (plus in-file callees: _(none)_)
- Target file(s): `train.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `get_lr_multiplier` (declared at module scope inside `autoresearch`) so that any post-training progress value (`progress >= 1.0`) is clamped to the final learning-rate fraction:
> 
> - Calling `get_lr_multiplier(progress)` with `progress >= 1.0` now returns the module-level constant `FINAL_LR_FRAC` directly. For example, `get_lr_multiplier(1.5)` returns `FINAL_LR_FRAC`, and `get_lr_multiplier(2.0)` returns `FINAL_LR_FRAC`.
> - Existing behaviour on `progress < 1.0` is preserved exactly, including the boundary case `progress == 1.0` which already evaluates to `FINAL_LR_FRAC` via the cooldown branch: `get_lr_multiplier(0.0)` returns `1.0` (the warmup branch when `WARMUP_RATIO` is `0`), `get_lr_multiplier(0.25)` returns `1.0` (the plateau between warmup end and `1.0 - WARMDOWN_RATIO`), `get_lr_multiplier(0.75)` returns `0.5`, and `get_lr_multiplier(1.0)` returns `FINAL_LR_FRAC`.
> 
> The minimal change is a single guard at the very top of the function body (before the warmup branch that consults `WARMUP_RATIO`) that short-circuits to `FINAL_LR_FRAC` when `progress >= 1.0`. Do NOT modify the existing warmup, plateau, or cooldown branches.

## Ground truth (reference edit)

`train.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def get_lr_multiplier(progress):
    if progress < WARMUP_RATIO:
        return progress / WARMUP_RATIO if WARMUP_RATIO > 0 else 1.0
    elif progress < 1.0 - WARMDOWN_RATIO:
        return 1.0
    else:
        cooldown = (1.0 - progress) / WARMDOWN_RATIO
        return cooldown * 1.0 + (1 - cooldown) * FINAL_LR_FRAC
```

```python
# newString
def get_lr_multiplier(progress):
    if progress >= 1.0:
        return FINAL_LR_FRAC
    if progress < WARMUP_RATIO:
        return progress / WARMUP_RATIO if WARMUP_RATIO > 0 else 1.0
    elif progress < 1.0 - WARMDOWN_RATIO:
        return 1.0
    else:
        cooldown = (1.0 - progress) / WARMDOWN_RATIO
        return cooldown * 1.0 + (1 - cooldown) * FINAL_LR_FRAC
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `get_lr_multiplier(0.0) == 1.0` |
| 2 | regression | over-edit | `get_lr_multiplier(0.25) == 1.0` |
| 3 | regression | over-edit | `get_lr_multiplier(0.75) == 0.5` |
| 4 | regression | over-edit | `get_lr_multiplier(1.0) == FINAL_LR_FRAC` |
| 5 | new_behavior | no-change | `get_lr_multiplier(1.5) == FINAL_LR_FRAC` |
| 6 | new_behavior | partial-edit | `get_lr_multiplier(2.0) == FINAL_LR_FRAC` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> ./` hits across these probes. The manifest pins D in `[2, 4]`:

- `def get_lr_multiplier` -> `./train.py`
- `WARMUP_RATIO` -> `./train.py`
- `tokenizer` -> `./README.md`, `./prepare.py`, `./program.md`, `./train.py`

- Union (D = 4): `./README.md`, `./prepare.py`, `./program.md`, `./train.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

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

1. `exec_assert` (`train.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `get_lr_multiplier(0.0) == 1.0` (kind: regression)
- **over-edit**: caught by `get_lr_multiplier(0.25) == 1.0` (kind: regression)
- **over-edit**: caught by `get_lr_multiplier(0.75) == 0.5` (kind: regression)
- **over-edit**: caught by `get_lr_multiplier(1.0) == FINAL_LR_FRAC` (kind: regression)
- **no-change**: caught by `get_lr_multiplier(1.5) == FINAL_LR_FRAC` (kind: new_behavior)
- **partial-edit**: caught by `get_lr_multiplier(2.0) == FINAL_LR_FRAC` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `get_lr_multiplier(2.0)` returns a negative LR multiplier from the cooldown branch (`no-change`).
- Adds a guard for `progress > 1.0` (strict inequality) but misses the `progress == 1.0` boundary case, leaving it to the cooldown branch which happens to also return `FINAL_LR_FRAC` -- so this looks fine but a stricter clamp would have caught it; conversely guarding on `progress > 1.0` instead of `>= 1.0` and accidentally changing the cooldown behaviour at the boundary breaks the regression on `progress == 1.0` (`partial-edit`).
- Clamps the progress argument itself (e.g. `progress = min(progress, 1.0)`) so other branches still execute, accidentally returning `1.0 * 1.0 + 0 * FINAL_LR_FRAC = 1.0` for clamped inputs rather than `FINAL_LR_FRAC` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
