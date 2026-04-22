# v1 #4 refactor_cosine_schedule

## Category

edit

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

## Pass criteria (4 checks)

1. `file_regex_disk` `train.py` `^SCHEDULE\s*=\s*["']trapezoid["']` — the new `SCHEDULE` module-level constant exists with the correct default string literal.
2. `file_regex_disk` `train.py` `def\s+get_lr_multiplier\(progress\)[\s\S]*?SCHEDULE\s*==\s*["']cosine["']` — the function body branches on `SCHEDULE == "cosine"`. Multiline match confirms the comparison is inside the function, not a stray string in the file.
3. `file_regex_disk` `train.py` `math\.cos\(\s*math\.pi\s*\*` — **hard-fact shape anchor**: the cosine call's argument begins with `math.pi * <expr>`. This is the canonical normalized-progress shape `0.5 * (1 + cos(pi * t))`; a model that wrote `math.cos(progress)` (wrong frequency) fails.
4. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

### Dropped: `any_tool_name_recursive: edit`

The tool-name check was removed in favor of pure results-oriented scoring. The three `file_regex_disk` anchors already verify the end state of the refactor (new constant, branch on it, canonical cosine shape). *How* the model got there — `edit`, `write`, or bash redirection — is irrelevant when the disk content is correct. Removing the anchor also eliminated a known false-fail mode where the fixture was pre-contaminated and the model sensibly refused to re-edit (see run `2026-04-22T05-18-24`).

Note on the residual ceiling: these checks pin formula *shape* but do not verify *runtime equivalence* (e.g., a sign error inside `0.5 * (1 + cos(...))` would pass). That's the known ceiling of static eval and is tracked as a follow-up via an out-of-scope exec evaluator.

### Dropped anchor (historical): `FINAL_LR_FRAC + (1 - FINAL_LR_FRAC)` interpolation

An earlier version of this sample included a sixth `file_regex_disk` anchor requiring the literal syntactic form `FINAL_LR_FRAC + (1 - FINAL_LR_FRAC)` in the cosine-branch return expression. It was dropped after a minimax-m2.5 run (`2026-04-22T18-17-15`) wrote a mathematically equivalent but syntactically different form:

```
return FINAL_LR_FRAC + 0.5 * (1.0 - FINAL_LR_FRAC) * (1.0 + math.cos(math.pi * t))
```

This is bit-identical at every input to the canonical `FINAL_LR_FRAC + (1.0 - FINAL_LR_FRAC) * 0.5 * (1.0 + cos(...))` — the `0.5` coefficient commutes with `(1 - FINAL_LR_FRAC)` — but the anchor regex only matched when `(1 - FINAL_LR_FRAC)` appeared directly after the `+`. That made the anchor brittle to a trivial commutative rewrite while adding no real correctness signal beyond what the `math.pi * <expr>` anchor already provides. The cosine-shape requirement (`0.5 * (1 + cos(pi * t))`) combined with the `FINAL_LR_FRAC` usage implied by the surrounding structure keeps the test honest without penalizing equivalent refactorings.

## Shortest path

**2-3 tool calls**: `read train.py` → `edit` (add `SCHEDULE` constant and restructure `get_lr_multiplier`) → optional second `edit` if split. Delegation to a subagent for the read half is permitted; recursive tool check accommodates this.

## Fail modes

- Missing `SCHEDULE` constant or wrong default — check 1 fails.
- Missing the `SCHEDULE == "cosine"` branch inside `get_lr_multiplier` — check 2 fails.
- Cosine called with wrong argument shape (`math.cos(progress)`, `math.cos(t)` without `math.pi *`) — check 3 fails. This is the most common hallucination mode.
- Model never modified the file — checks 1–3 all fail because the disk still shows the baseline.
- Interpolation endpoint wrong (e.g., decays to `0` instead of `FINAL_LR_FRAC`) — not directly checked statically (residual ceiling; see dropped-anchor note above).
- Trapezoid branch mutated even when `SCHEDULE == "trapezoid"` — not directly checked statically (residual ceiling; exec would catch it).
- Malformed tool args on whatever path was taken — `call_schema_valid` fails.
