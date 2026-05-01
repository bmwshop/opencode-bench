# v1 #14 synthesize_schedule_repro

## Category

code_authoring (artifact-creation family: write a runnable reproduction
script from scratch given a target API spec).

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The
agent operates in a per-run copy of the submodule checkout at
`projects/v1/autoresearch/`.

## Capability

The issue-reproduction atomic skill (per Ma et al. arXiv:2604.05013):
produce a runnable script that exercises a target API and emits a
specific output shape, without mutating the repo under study. Tests
whether the model can (a) read a target helper to derive the ground-truth
values it produces at five chosen probe points, (b) write a `print()`
loop that emits a strict line format, and (c) leave the source untouched
(implicitly, via the verifier's stub-build invariant -- see below).

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`.
`reproduce.py` does not pre-exist.

`train.py` defines a trapezoidal learning-rate schedule helper. With
its current constants the schedule yields five deterministic values at
the probe points:

- `progress=0.0` → `lrm=1.0`
- `progress=0.25` → `lrm=1.0` (plateau)
- `progress=0.5` → `lrm=1.0` (end of plateau)
- `progress=0.75` → `lrm=0.5` (half cooldown:
  `0.5 * 1.0 + 0.5 * FINAL_LR_FRAC`)
- `progress=1.0` → `lrm=0.0` (= `FINAL_LR_FRAC`)

## De-leak status

Function name (`get_lr_multiplier`), constant names, and the five
expected return values are deliberately omitted from the prompt. The
output format spec (`progress=<p> lrm=<v>`) is fixed and named because
it is part of the verifier's contract. File path `reproduce.py` is fixed
(verifier's contract). Source file `train.py` is named (it is the only
training script in the repo and is unavoidably part of the import
contract).

## Prompt

> In this `autoresearch` repo, the training script `train.py` defines a
> learning-rate schedule helper. Create a script `reproduce.py` at the
> repo root that:
>
> - Imports the helper from the `train` module (the per-run fixture
>   stubs `train.py` to be safely importable in isolation;
>   `from train import ...` resolves through PYTHONPATH).
> - For each progress value in `[0.0, 0.25, 0.5, 0.75, 1.0]`, computes
>   the helper's return value and prints exactly one line in the
>   format `progress=<p> lrm=<v>` (literal substrings `progress=` and
>   ` lrm=`; values are Python's default `str()` formatting).
> - Does NOT modify `train.py`. The expected values are determined by
>   reading the helper plus its three controlling module-level
>   constants -- derive them from source.
>
> Runnable as `python reproduce.py`.

## Pass criteria (2 checks)

1. `exec_function` `script=reproduce.py`, `source=train.py`,
   `functions=[get_lr_multiplier]`,
   `expect_stdout_contains=["progress=0.25 lrm=1.0",
   "progress=0.75 lrm=0.5", "progress=1.0 lrm=0.0"]`, `timeout=10s`.
   Passes iff the stub builds, the subprocess exits 0, and all three
   needles appear in stdout. The three discriminating progress values
   collectively fix the schedule shape: plateau at 0.25, half-cooldown
   interpolation at 0.75, endpoint at 1.0. The plateau-left values at
   `progress=0.0` and `progress=0.5` are not pinned because they are
   trivially satisfied by any plausible schedule.
2. `call_schema_valid` — every tool call in the trace matches
   opencode's canonical JSON schemas.

### Why the train.py-untouched invariant is implicit

Under execution, `train.py`'s constants are the *only* place the three
expected stdout values can come from: the stub is built by extracting
the real `train.py`'s top-level literal `WARMUP_RATIO` /
`WARMDOWN_RATIO` / `FINAL_LR_FRAC` plus the helper function's source.
If the model edits any of those constants, the stub reflects the edit,
the student's script computes the modified schedule, and the resulting
stdout no longer contains `progress=0.75 lrm=0.5` (or the other pinned
strings) — the check fails. The only evasion would be to modify
`train.py` *and* hardcode pre-modification stdout literals, which
defeats the model's own edit and is not a realistic gaming vector.

## Shortest path

**2 tool calls**: `read train.py` → `write reproduce.py`. A model that
derived the five ground-truth values without reading would need to
guess `WARMDOWN_RATIO=0.5` and `FINAL_LR_FRAC=0.0` for the half-cooldown
and endpoint values.

## Fail modes

- **Script not created** — `exec_function` reports
  `script not found: reproduce.py`.
- **Wrong import path / import of a non-exported name** — subprocess
  fails with `ImportError`.
- **Script error at runtime** (bad formatting, attribute typo, type
  error in the loop) — subprocess fails with non-zero exit; the last
  stderr line is surfaced.
- **Wrong value at `progress=0.25`** (e.g. `lrm=0.75` under a
  hallucinated cosine schedule) — stdout missing
  `'progress=0.25 lrm=1.0'`.
- **Wrong value at `progress=0.75`** (most common error: forgetting the
  cooldown interpolation, printing `lrm=1.0` or `lrm=0.0` instead) —
  stdout missing `'progress=0.75 lrm=0.5'`.
- **Wrong endpoint** — stdout missing `'progress=1.0 lrm=0.0'`.
- **Model edited `train.py`** (e.g. changed `FINAL_LR_FRAC`) — stub
  inherits the edit, script emits modified values, pinned needles no
  longer match.
- **Runaway script** — 10s timeout fires.
- **Fixture damage** — harness-level reason (source `SyntaxError` /
  target function not found).
- **Malformed tool args** — `call_schema_valid` fails.

## Known ceilings

- A model that hardcodes the three expected strings as `print` literals
  — without actually calling the helper — passes. Acceptable: the
  model still had to know the ground-truth numbers to emit them, which
  is the substantive capability this sample measures.

## Note on methodology

This sample is part of v1's three-sample artifact-creation family
(#13, #14, #15). Reference: Ma et al. arXiv:2604.05013, "atomic
skills" taxonomy, issue-reproduction skill.
