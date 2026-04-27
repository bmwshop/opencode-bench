# v1 #13 synthesize_schedule_tests

## Category

code_authoring (artifact-creation family: write a runnable test script from
scratch given a target API spec).

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The
agent operates in a per-run copy of the submodule checkout at
`projects/v1/autoresearch/`.

## Capability

The artifact-creation atomic skill (per Ma et al. arXiv:2604.05013):
read a target API in the repo, derive the API's current behavior at three
discriminating inputs by reasoning about the source, and produce a
runnable Python test script that asserts those values. Tests whether the
model can (a) locate the relevant helper without being told its name,
(b) read the helper plus its controlling constants and compute the
expected return values, and (c) write a syntactically clean test file
that exits non-zero on assertion failure.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. The
`tests/` directory does not exist yet; the model creates it. No
`tests/test_schedule.py` pre-exists.

`train.py` (the only top-level Python file in the repo) defines a
trapezoidal learning-rate schedule helper. With the file's current
constants the schedule is fully deterministic: at `progress=0.0` it
returns `1.0` (warmup is skipped because the warmup-ratio constant is
`0.0`), at `progress=0.25` it returns `1.0` (plateau, because the
warmdown ratio is `0.5`), and at `progress=1.0` it returns `0.0`
(`FINAL_LR_FRAC` endpoint).

## De-leak status

Function name (`get_lr_multiplier`), constant names, and the three
expected return values are deliberately omitted from the prompt. The
model must derive all three by reading the source. File path
`tests/test_schedule.py` is fixed (it is the verifier's contract) and
the source file `train.py` is named (it is the only training script in
the repo and is unavoidably part of the import contract).

## Prompt

> In this `autoresearch` repo, the training script `train.py` defines a
> learning-rate schedule helper -- a small function that takes a single
> `progress` argument in `[0.0, 1.0]` and returns the learning-rate
> multiplier under a trapezoidal schedule controlled by three
> module-level constants. Read the helper and its constants to derive
> its current behavior, then create a test script at
> `tests/test_schedule.py` that:
>
> - Imports the helper from the `train` module (the per-run fixture
>   stubs `train.py` to be safely importable in isolation;
>   `from train import ...` resolves through PYTHONPATH).
> - Uses three plain `assert` statements to verify the helper's current
>   return value at three discriminating progress values: `0.0`,
>   `0.25`, and `1.0`. Derive the three correct expected values from
>   the helper's source -- do NOT hardcode arbitrary numbers and do
>   NOT modify `train.py`.
> - Prints exactly the line `ok` on success.
> - Exits non-zero (via `AssertionError`) on any assertion failure.
>
> Runnable as `python tests/test_schedule.py`.

## Pass criteria (2 checks)

1. `exec_function` `script=tests/test_schedule.py`, `source=train.py`,
   `functions=[get_lr_multiplier]`, `expect_stdout_contains="ok"`,
   `timeout=10s`. Passes iff (a) the stub builds (source parses,
   `get_lr_multiplier` extractable), (b) the subprocess exits 0, and
   (c) `ok` appears in stdout. One failed assertion inside the
   student's script produces a non-zero exit which fails this check
   with the trailing stderr line surfaced as the reason.
2. `call_schema_valid` — every tool call in the trace matches
   opencode's canonical JSON schemas.

### Why the test runs against an AST stub, not the real `train.py`

`train.py`'s top-level imports include `import torch` and other
side-effectful kernel-loading calls that would fail in a CI-style eval
environment regardless of the model's edit. `exec_function` instead
extracts the named function plus every top-level literal `Assign` /
`AnnAssign` from the source into a side-effect-free stub at the
mirrored relative path under a tempdir, then prepends that tempdir to
`PYTHONPATH` so the student's `from train import …` resolves to the
stub. The student script still sees `__file__ = <abs script path>`,
`__name__ = '__main__'`, and `cwd = <project_dir>`, so normal script
semantics are preserved.

## Shortest path

**2 tool calls**: `read train.py` (to confirm the schedule logic and
derive the ground-truth values) → `write tests/test_schedule.py`. A
model that already knows the schedule's shape could in principle skip
the read, but it would have to guess `WARMUP_RATIO = 0.0`,
`WARMDOWN_RATIO = 0.5`, `FINAL_LR_FRAC = 0.0` (the file's current
literals) without seeing them.

## Fail modes

- **Script not created** — `exec_function` reports
  `script not found: tests/test_schedule.py`.
- **Wrong import path** (e.g. `from train import schedule`) —
  subprocess fails with `ImportError: cannot import name 'schedule'`.
- **Wrong assertion value** (e.g. `assert get_lr_multiplier(0.25) ==
  0.75`, hallucinating a cosine schedule) — subprocess fails with
  `AssertionError`.
- **Missing constant import** when the test references a constant by
  name without importing it — subprocess fails with
  `NameError: name 'FINAL_LR_FRAC' is not defined`.
- **Missing or mis-spelled success signal** (no `print("ok")`, or
  printed a different string) — `expect_stdout_contains` fails:
  `stdout missing 'ok'`.
- **Runaway script** — 10s timeout fires; reason
  `exec_function script timeout after 10s`.
- **Fixture damage** (source `SyntaxError` or target function removed
  by an unintended edit) — harness-level reason: `SyntaxError in
  train.py …` / `function 'get_lr_multiplier' not found`.
- **Malformed tool args** on whatever path was taken — `call_schema_valid`
  fails.

## Known ceilings

- A script that only does `print("ok")` with no asserts passes — the
  prompt asks for asserts but the verifier alone cannot enforce their
  existence. Acceptable here because the model still had to know the
  three correct values to pass the discriminating-needle variants
  #14 and #15 of this family, which makes a `print("ok")`-only solver
  catastrophically narrow.
- A test script that imports unlisted helpers transitively (the
  `get_lr_multiplier` body uses only arithmetic on the three constants
  plus `math` -- which is not currently imported in the stub) would
  `NameError` at runtime. For the current schedule logic this never
  bites.

## Note on methodology

This sample is part of v1's three-sample artifact-creation family
(#13, #14, #15) covering the "synthesize a runnable script that
exercises a target API" skill. The family applies the same de-leak
discipline as the editing tier (#51-#80): function names and expected
values are hidden in the prompt; the verifier executes the artifact and
checks discriminating output needles. Reference: Ma et al.
arXiv:2604.05013, "atomic skills" taxonomy.
