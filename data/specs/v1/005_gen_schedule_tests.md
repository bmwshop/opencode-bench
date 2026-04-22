# v1 #5 gen_schedule_tests

## Category

test_generation

## Contract

completion

## Surface

tools

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Unit-test generation against real training code. `train.py` defines `get_lr_multiplier(progress)` at line 518 as a trapezoidal schedule. With the file's current constants (`WARMUP_RATIO=0.0`, `WARMDOWN_RATIO=0.5`, `FINAL_LR_FRAC=0.0`), the schedule is fully deterministic — at `progress=0.0` it returns `1.0` (warmup skipped), at `progress=0.25` it returns `1.0` (plateau), at `progress=1.0` it returns `FINAL_LR_FRAC` (endpoint). This sample asks the model to produce a runnable test script that encodes those three specific return values as `assert` statements. Tests the unit-test-generation atomic skill (per Ma et al. arXiv:2604.05013): the model must read the schedule logic, derive the ground-truth return values at three probe points, and encode them as assertions against `get_lr_multiplier`.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. The `tests/` directory does not exist yet; the model creates it. No `tests/test_schedule.py` pre-exists.

## Prompt

> Create tests/test_schedule.py that imports get_lr_multiplier from train and uses plain assert statements to verify: (a) get_lr_multiplier(0.0) == 1.0, (b) get_lr_multiplier(1.0) == FINAL_LR_FRAC (import it too), (c) get_lr_multiplier(0.25) == 1.0. Runnable as `python tests/test_schedule.py`; print "ok" on success.

## Pass criteria (5 checks)

1. `file_regex_disk` `tests/test_schedule.py` `from\s+train\s+import[^\n]*get_lr_multiplier` — the script imports the target symbol from `train`. (An import of `FINAL_LR_FRAC` is also required semantically; we rely on the next check's source-level reference to `FINAL_LR_FRAC` to indirectly verify its presence. A dedicated `FINAL_LR_FRAC` import regex was dropped as redundant with that reference.)
2. `file_regex_disk` `tests/test_schedule.py` `assert\s+get_lr_multiplier\(\s*0\.25\s*\)\s*==\s*1(?:\.0)?` — **hard-fact anchor**: the assertion encodes the ground truth that `get_lr_multiplier(0.25) == 1.0` (plateau; requires knowing the plateau extends to `1.0 - WARMDOWN_RATIO = 0.5`).
3. `file_regex_disk` `tests/test_schedule.py` `assert\s+get_lr_multiplier\(\s*1(?:\.0)?\s*\)\s*==\s*FINAL_LR_FRAC` — **hard-fact anchor**: the assertion encodes the endpoint fact `get_lr_multiplier(1.0) == FINAL_LR_FRAC` and forces the test to reference `FINAL_LR_FRAC` symbolically (implying the import was performed).
4. `file_regex_disk` `tests/test_schedule.py` `print\(["']ok["']\)` — the success indicator as specified in the prompt.
5. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

Note on drops vs the initial draft: the `assert get_lr_multiplier(0.0) == 1.0` anchor from the prompt is not checked, because it's trivially satisfied (every reasonable LR schedule returns `1.0` at progress `0.0`). The two kept assertions are the distinctive hard facts.

### Dropped: `any_tool_name_recursive: write`

The tool-name check was removed in favor of pure results-oriented scoring. The four `file_regex_disk` anchors already verify that `tests/test_schedule.py` exists on disk with the required content. *How* the model created it — `write`, `edit` with empty `oldString`, or even `bash cat > ...` redirection — is irrelevant when the final file is correct. `call_schema_valid` still catches malformed calls on whatever path was taken.

## Shortest path

**2 tool calls**: `read train.py` (to confirm the schedule logic and derive the ground-truth values) → `write tests/test_schedule.py`. A model that already knows the schedule's shape could skip the read.

## Fail modes

- No file created — all content checks fail because the disk file is missing.
- Import missing or wrong path (e.g., `from get_lr_multiplier import ...`) — check 1 fails.
- Assertion for `progress=0.25` encodes a wrong value (e.g., `== 0.75`) — check 2 fails. This is the discriminative anchor: a model that hallucinated a cosine schedule would put a non-`1.0` value here.
- Assertion for `progress=1.0` uses a literal `0.0` instead of `FINAL_LR_FRAC` — check 3 fails. Even though the literal `0.0` equals the ground-truth value, the regex requires the symbolic form, which forces the import.
- Missing `print("ok")` — check 4 fails.
- Malformed tool args on whatever path was taken — `call_schema_valid` fails.
