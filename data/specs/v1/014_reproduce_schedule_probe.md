# v1 #14 reproduce_schedule_probe

## Category

tool_schema

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

The model is asked to write `reproduce.py` that prints these five lines in the exact format `progress=<p> lrm=<v>`. `reproduce.py` is verified by execution, not regex: the `exec_function` evaluator AST-extracts `get_lr_multiplier` plus every top-level literal constant from `train.py` into a side-effect-free stub module, injects it on `sys.path`, and runs the student's script. Because the stub is built *from the current `train.py` on disk*, the five expected stdout lines are a behavioral consequence of "correct schedule + untouched constants" — the check captures both the computation and the repo-untouched invariant in one probe.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. `reproduce.py` does not pre-exist.

## Prompt

> Create reproduce.py at the repo root. It must (1) import get_lr_multiplier from train and (2) print one line per progress value for progress in [0.0, 0.25, 0.5, 0.75, 1.0], formatted exactly as `progress=<p> lrm=<v>`. Runnable as `python reproduce.py`. Do not modify train.py.

## Pass criteria (2 checks)

1. `exec_function` script=`reproduce.py`, source=`train.py`, functions=`[get_lr_multiplier]`, `expect_stdout_contains=["progress=0.25 lrm=1.0", "progress=0.75 lrm=0.5", "progress=1.0 lrm=0.0"]`, timeout=10s. Passes iff the stub builds, the subprocess exits 0, and all three needles appear in stdout. The three discriminative progress values collectively fix the schedule shape: plateau value at 0.25, half-cooldown interpolation at 0.75, endpoint at 1.0. The plateau-left values at `progress=0.0` and `progress=0.5` are not pinned because they are trivially satisfied by any reasonable schedule.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

### Why the train.py-untouched invariant is implicit

Under execution, `train.py`'s constants are the *only* place the three expected stdout values can come from: the stub is built by extracting the real `train.py`'s top-level literal `WARMUP_RATIO`/`WARMDOWN_RATIO`/`FINAL_LR_FRAC` plus the `get_lr_multiplier` function source. If the model edits any of those constants, the stub reflects the edit, the student's script computes the modified schedule, and the resulting stdout no longer contains `progress=0.75 lrm=0.5` (or the other pinned strings) — the check fails.

The only evasion path would be to modify `train.py` *and* produce pre-modification stdout anyway (e.g., `print('progress=0.25 lrm=1.0')` as a hardcoded literal). That defeats the model's own edit to the repo, so the behavior is self-defeating and not a realistic gaming vector. A dedicated "train.py untouched" check therefore adds no independent signal.

### Known ceilings

- A model that hardcodes the three expected strings as `print` literals — without actually calling `get_lr_multiplier` — passes. Deemed acceptable: the model still had to know the ground-truth numbers to emit them, which is the substantive capability this sample measures.
- Same limitations as #13 regarding unlisted helper functions and decorated target functions; not triggered by `get_lr_multiplier`'s arithmetic-only body.

## Shortest path

**2 tool calls**: `read train.py` → `write reproduce.py`. A model that derives the five ground-truth values without reading cannot reliably emit the half-cooldown `lrm=0.5` or the endpoint `lrm=0.0` because it would need to know `WARMDOWN_RATIO=0.5` and `FINAL_LR_FRAC=0.0` from the actual file state (not from a hallucinated default).

## Fail modes

- **Script not created** — `exec_function` reports `script not found: reproduce.py`.
- **Wrong import path / import of a non-exported name** — subprocess fails with `ImportError`.
- **Script error at runtime** (bad formatting, wrong attribute, bad slicing) — subprocess fails with non-zero exit; the last stderr line is surfaced.
- **Wrong value at `progress=0.25`** (e.g. `lrm=0.75` under a hallucinated cosine schedule) — stdout missing `'progress=0.25 lrm=1.0'`.
- **Wrong value at `progress=0.75`** (the most common error: forgetting the cooldown interpolation) — stdout missing `'progress=0.75 lrm=0.5'`.
- **Wrong endpoint** — stdout missing `'progress=1.0 lrm=0.0'`.
- **Model edited `train.py`** (e.g. changed `FINAL_LR_FRAC`) — the stub inherits the edit, the script emits modified values, and the pinned needles no longer match stdout. Reason names the first missing needle.
- **Runaway script** — 10s timeout fires.
- **Fixture damage** — harness-level reason (source `SyntaxError` / target function not found); indicates the fixture was damaged prior to evaluation.
- **Malformed tool args** on whatever path was taken — `call_schema_valid` fails.
