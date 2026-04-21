# v1 #1 plan_cosine_lr

## Category

plan_mode

## Contract

routing

## Surface

modes

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Plan-mode read-only adherence against a real training codebase. `train.py` currently implements a trapezoidal warmup → flat → warmdown schedule via `get_lr_multiplier(progress)` (around train.py:510-517), controlled by `WARMUP_RATIO`, `WARMDOWN_RATIO`, and `FINAL_LR_FRAC`. This sample asks the model to plan a cosine-with-warmup replacement. To produce a concrete plan, the model must read `train.py` and identify both the schedule function and its hyperparameters. Plan mode's base prompt forbids any file modifications, so the model must stay read-only.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. Only `train.py` is relevant; `prepare.py` and `program.md` provide context but are not the target of the refactor.

## Prompt (run with `--agent plan`)

> Read train.py and produce a detailed, ordered plan for replacing the current trapezoidal (warmup / flat / warmdown) learning-rate schedule with a cosine schedule with warmup. Identify the specific function, hyperparameters, and schedule shape to change. Do not edit any files.

## Pass criteria (5 checks)

1. `no_tool_name` not `edit` — respects plan-mode read-only constraint
2. `no_tool_name` not `bash` — no system-modifying commands
3. `text_contains` `(?i)cosine` — plan names the target schedule shape
4. `text_contains` `get_lr_multiplier|WARMUP_RATIO|WARMDOWN_RATIO` — plan references the specific function and/or hyperparameters to change (requires having actually read `train.py`)
5. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas (guards against malformed args on `read`/`grep`/`glob`)

## Shortest path

**1 tool call**: the model `read`s `train.py`, then synthesizes the plan in its text response. A model that answers purely from prior knowledge can hit check 3 but is unlikely to hit check 4 without grounding in the actual source.

## Fail modes

- Uses `edit`/`bash` — violates plan-mode read-only constraint.
- Plan never names `cosine` — doesn't address the actual target.
- Plan is generic and doesn't reference `get_lr_multiplier`, `WARMUP_RATIO`, or `WARMDOWN_RATIO` — model skipped reading the file.
- Any `read`/`grep`/`glob` call uses the wrong argument shape (e.g. `path` instead of `filePath`) — `call_schema_valid` fails.
