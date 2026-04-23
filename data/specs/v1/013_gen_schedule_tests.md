# v1 #13 gen_schedule_tests

## Category

tool_schema

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Unit-test generation against real training code. `train.py` defines `get_lr_multiplier(progress)` at line 518 as a trapezoidal schedule. With the file's current constants (`WARMUP_RATIO=0.0`, `WARMDOWN_RATIO=0.5`, `FINAL_LR_FRAC=0.0`), the schedule is fully deterministic — at `progress=0.0` it returns `1.0` (warmup skipped), at `progress=0.25` it returns `1.0` (plateau; requires knowing the plateau extends to `1.0 - WARMDOWN_RATIO = 0.5`), at `progress=1.0` it returns `FINAL_LR_FRAC` (endpoint). This sample asks the model to produce a runnable test script that encodes those three return values as `assert` statements. Tests the unit-test-generation atomic skill (per Ma et al. arXiv:2604.05013): the model must read the schedule logic, derive the ground-truth return values at three probe points, and encode them as assertions against `get_lr_multiplier`.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. The `tests/` directory does not exist yet; the model creates it. No `tests/test_schedule.py` pre-exists.

## Prompt

> Create tests/test_schedule.py that imports get_lr_multiplier from train and uses plain assert statements to verify: (a) get_lr_multiplier(0.0) == 1.0, (b) get_lr_multiplier(1.0) == FINAL_LR_FRAC (import it too), (c) get_lr_multiplier(0.25) == 1.0. Runnable as `python tests/test_schedule.py`; print "ok" on success.

### Verifier mechanism

The test script is verified by **execution**. The `exec_function` evaluator AST-extracts `get_lr_multiplier` plus every top-level literal constant from `train.py` into a side-effect-free stub module at `<tempdir>/train.py`, injects `<tempdir>` at the head of `sys.path` via a runner wrapper, then runs `python tests/test_schedule.py` with `cwd = <project>`. The student's `from train import …` resolves to the stub; the script runs under real Python semantics — no torch, no CUDA, no import-time explosion from the real `train.py`'s top-level side effects.

## Pass criteria (2 checks)

1. `exec_function` script=`tests/test_schedule.py`, source=`train.py`, functions=`[get_lr_multiplier]`, `expect_stdout_contains="ok"`, timeout=10s. Passes iff (a) the stub builds (source parses, `get_lr_multiplier` present), (b) the subprocess exits 0, (c) `ok` appears in stdout. One failed assertion inside the student's script produces a non-zero exit, which fails this check with an `AssertionError` reason.
2. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

### Known ceilings

- A script that only does `print("ok")` with no asserts passes — the prompt asks for asserts but the verifier alone cannot enforce their existence. Not observed as a gaming vector.
- If the student's `get_lr_multiplier` body (extracted from the fixture) were to call an unlisted helper, the subprocess would `NameError` at runtime. For the current `get_lr_multiplier` (arithmetic only) this doesn't bite.

## Shortest path

**2 tool calls**: `read train.py` (to confirm the schedule logic and derive the ground-truth values) → `write tests/test_schedule.py`. A model that already knows the schedule's shape could skip the read.

## Fail modes

- **Script not created** — `exec_function` reports `script not found: tests/test_schedule.py`.
- **Wrong import path / import of a non-exported name** (e.g. `from train import fa3`) — subprocess fails with `ImportError`; the reason surfaces the missing name.
- **Wrong assertion value** (e.g. `assert get_lr_multiplier(0.25) == 0.75`) — subprocess fails with `AssertionError`.
- **Missing `FINAL_LR_FRAC` import** (used without importing it) — subprocess fails with `NameError: name 'FINAL_LR_FRAC' is not defined`.
- **Missing or mis-spelled success signal** (no `print("ok")`, or printed a different string) — `expect_stdout_contains` fail: `stdout missing 'ok'`.
- **Runaway script** — 10s timeout fires; reason `exec_function script timeout after 10s`.
- **Fixture damage** (source `SyntaxError` or target function removed) — harness-level reason (`SyntaxError in train.py …` / `function 'get_lr_multiplier' not found`); indicates the fixture was damaged prior to evaluation.
- **Malformed tool args** on whatever path was taken — `call_schema_valid` fails.
