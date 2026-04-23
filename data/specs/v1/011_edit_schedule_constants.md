# v1 #11 edit_schedule_constants

## Category

tool_schema

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Small-scope atomic edit against real training code. `train.py` defines three schedule constants at lines 445-447 (`WARMUP_RATIO`, `WARMDOWN_RATIO`, `FINAL_LR_FRAC`). This sample asks the model to update two of the three values to concrete new numbers while leaving the third at its current value. Tests the canonical "change constant" edit primitive (atomic skill: editing per Ma et al. arXiv:2604.05013) and whether the model uses the proper `edit` tool rather than bash-as-editor.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. Only the three `*_RATIO` / `FINAL_LR_FRAC` lines in `train.py` are relevant.

## Prompt

> In train.py, change WARMUP_RATIO from 0.0 to 0.05 and FINAL_LR_FRAC from 0.0 to 0.1. Keep WARMDOWN_RATIO at 0.5. Minimal changes only.

## Pass criteria (2 checks)

1. `exec_assert` `train.py` — AST-extracts the three schedule constants and `get_lr_multiplier` into an isolated `python3` subprocess and runs six assertions. All six must pass for the check to pass; on failure the first failing assert is the reason. Asserts:
   - `WARMUP_RATIO == 0.05` — updated constant.
   - `FINAL_LR_FRAC == 0.1` — updated constant.
   - `WARMDOWN_RATIO == 0.5` — preservation constraint.
   - `get_lr_multiplier(0.025) == 0.5` — mid-warmup behavior probe; equals `0.5` iff `WARMUP_RATIO == 0.05` AND the linear-warmup branch is intact.
   - `get_lr_multiplier(0.25) == 1.0` — plateau probe; equals `1.0` iff warmup ended at `0.05` and warmdown starts at `1.0 - WARMDOWN_RATIO = 0.5`.
   - `get_lr_multiplier(1.0) == 0.1` — endpoint probe; equals `FINAL_LR_FRAC == 0.1` by construction of the cooldown branch.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

### Why AST extraction rather than plain `import train`

`train.py` has side-effectful top-level imports (`import torch`, `from kernels import get_kernel`, `from prepare import ...`). A normal import would fail in the eval environment regardless of the model's changes. `exec_assert` surgically extracts only the three `ast.Assign` nodes and the `get_lr_multiplier` `ast.FunctionDef`, binds constants via `ast.literal_eval`, and `exec`s the function body in an isolated namespace where the only available names are the extracted constants and builtins.

## Shortest path

**2 tool calls**: one `read` on `train.py` to locate the constants, one `edit` to apply both value changes (opencode's `edit` tool accepts multiple replacements per call via repeated `oldString`/`newString` pairs, so a single edit can update both lines). A model that already knows the file layout can skip the read and do just one `edit`, in which case the `min_calls: 2` floor is the only gate.

## Fail modes

- Wrong value written (e.g. `WARMUP_RATIO = 0.5`) — the corresponding `... == ...` assert fails.
- Model never modified the file (e.g. stopped mid-turn, answered conversationally) — the first assert (`WARMUP_RATIO == 0.05`) fails against the baseline `0.0`.
- Over-edit that changes `WARMDOWN_RATIO` away from `0.5` — caught directly by the `WARMDOWN_RATIO == 0.5` assert, and in most mis-edits also by the `lrm(0.25)` / `lrm(1.0)` behavior probes.
- Function body broken (e.g. dropped `else` branch, swapped constants, wrong sign) — at least one of the three `get_lr_multiplier(...) == ...` probes fails with `assert failed: get_lr_multiplier(...) == ...`.
- Non-literal RHS introduced (e.g. `WARMUP_RATIO = float("0.05")` or `= compute()`) — `ast.literal_eval` on the value node fails; reason: `constant 'WARMUP_RATIO' not a literal: ...`.
- Constant or function deleted entirely — reason: `constant 'X' not found` or `function 'get_lr_multiplier' not found`.
- Syntax error introduced in `train.py` — `ast.parse` fails; reason: `SyntaxError at line N: ...`.
- Infinite loop added to the function body (pathological, but possible) — the per-check 5s `timeout` fires; reason: `exec_assert timeout after 5s`.
- Malformed tool args on whatever path was taken — `call_schema_valid` fails.
