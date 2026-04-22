# v1 #6 reproduce_schedule_probe

## Category

reproduction

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Issue-reproduction atomic skill (per Ma et al. arXiv:2604.05013): produce a runnable script that exercises a target API and emits a specific output shape, without mutating the repo under study. `train.py` defines `get_lr_multiplier(progress)` as a trapezoidal schedule; with current constants it yields deterministic values at the five probe points:

- `progress=0.0` → `lrm=1.0`
- `progress=0.25` → `lrm=1.0` (plateau)
- `progress=0.5` → `lrm=1.0` (end of plateau)
- `progress=0.75` → `lrm=0.5` (half cooldown: `0.5 * 1.0 + 0.5 * FINAL_LR_FRAC`)
- `progress=1.0` → `lrm=0.0` (= `FINAL_LR_FRAC`)

The model is asked to write `reproduce.py` that prints these five lines in the exact format `progress=<p> lrm=<v>` and, at the top of the file, to include a `# expected:` comment block listing the five expected stdout lines. The comment-block requirement is the mechanism that pulls the ground-truth values into the file source as literal strings (without it, a script like `print(f"progress={p} lrm={get_lr_multiplier(p)}")` would not contain the literal values anywhere we could `file_regex`-check statically).

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. `reproduce.py` does not pre-exist.

## Prompt

> Create reproduce.py at the repo root. It must: (1) import get_lr_multiplier from train, (2) at the top of the file include a comment block beginning with `# expected:` that lists, on separate lines, each of the five expected stdout lines the script will print, and (3) print one line per progress value for progress in [0.0, 0.25, 0.5, 0.75, 1.0], formatted exactly as `progress=<p> lrm=<v>`. Do not modify train.py.

## Pass criteria (7 checks)

1. `any_tool_name_recursive` `write` — the `write` tool was invoked to create `reproduce.py`.
2. `file_regex` `reproduce.py` `from\s+train\s+import[^\n]*get_lr_multiplier` — the script imports the target symbol.
3. `file_regex` `reproduce.py` `progress=0\.25 lrm=1\.0` — **hard-fact anchor**: distinctive plateau value; a model that hallucinated a cosine decay would emit a non-`1.0` value here.
4. `file_regex` `reproduce.py` `progress=0\.75 lrm=0\.5` — **hard-fact anchor**: the half-cooldown value, most discriminative of the five (requires correct cooldown interpolation `0.5 * 1.0 + 0.5 * FINAL_LR_FRAC = 0.5`).
5. `file_regex` `reproduce.py` `progress=1\.0 lrm=0\.0` — **hard-fact anchor**: endpoint `= FINAL_LR_FRAC = 0.0`.
6. `file_regex` `train.py` `^WARMUP_RATIO\s*=\s*0\.0\b` — **repo-untouched invariant**: `train.py`'s first schedule constant is unchanged. The prior `no_tool_name_recursive: edit` guard was dropped as redundant: this regex is strictly stronger because it also catches bash-sed edits.
7. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

Note on drops vs the initial draft: the two trivially-satisfied plateau anchors (`progress=0.0 lrm=1.0` and `progress=0.5 lrm=1.0`) and the standalone `# expected:` marker regex were removed. The three kept value anchors are each independently discriminative; if they all match, the `# expected:` block content has been produced regardless of whether a literal `# expected:` label is present.

## Shortest path

**2 tool calls**: `read train.py` → `write reproduce.py`. A model that derives the five ground-truth values without reading cannot reliably satisfy checks 3-5 because it would need to know `WARMDOWN_RATIO=0.5` and `FINAL_LR_FRAC=0.0` from the actual file state (not from a hallucinated default).

## Fail modes

- No file created — check 1 fails.
- Import missing — check 2 fails.
- Wrong value for `progress=0.25` (e.g., `lrm=0.75` under a hallucinated cosine schedule) — check 3 fails.
- Wrong value for `progress=0.75` (most common error: forgetting the cooldown formula and emitting `lrm=1.0` or `lrm=0.25`) — check 4 fails.
- Wrong endpoint — check 5 fails.
- Model edited `train.py` (via any tool) — check 6 fails.
- Malformed `write` args — `call_schema_valid` fails.
