# v1 #3 edit_schedule_constants

## Category

edit

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

## Pass criteria (4 checks)

1. `any_tool_name_recursive` `edit` — the `edit` tool was invoked at least once (parent or subagent). Recursive wrapper so delegation is not penalized.
2. `file_regex` `train.py` `WARMUP_RATIO\s*=\s*0\.05\b` — hard fact: the new warmup value is exactly `0.05`.
3. `file_regex` `train.py` `FINAL_LR_FRAC\s*=\s*0\.1\b` — hard fact: the new final-LR fraction is exactly `0.1`.
4. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

Note on the dropped WARMDOWN preservation anchor: the `file_regex` evaluator scans concatenated `newString` values from `write`/`edit` calls against the target path (and only falls back to the disk file when *no* such calls touched it). Because a correct minimal edit of `train.py` touches only the WARMUP and FINAL lines, the WARMDOWN line never appears in any `newString`, so an anchor on `WARMDOWN_RATIO = 0.5` would false-fail on a correct model and also fail on an over-edit that mutated WARMDOWN — no discriminative power either way. Dropping it leaves correctness-testing on exactly the two values the model was asked to change. The `^` line-start anchors were also dropped from anchors 2 and 3 for the same concatenation reason: successive edit `newString`s are glued without a separator, so `^` under `re.MULTILINE` cannot land between them. `\b` at the end of each numeric literal is sufficient to prevent `0.05` from matching `0.050` / `0.1` from matching `0.10`.

## Shortest path

**2 tool calls**: one `read` on `train.py` to locate the constants, one `edit` to apply both value changes (opencode's `edit` tool accepts multiple replacements per call via repeated `oldString`/`newString` pairs, so a single edit can update both lines). A model that already knows the file layout can skip the read and do just one `edit`, in which case the `min_calls: 2` floor is the only gate.

## Fail modes

- Model edits via `bash sed -i` — `any_tool_name_recursive: edit` fails because no edit tool was invoked. (The prior explicit `no_tool_name_recursive: bash` guard was dropped as redundant: if bash-sed was used instead of `edit`, the edit-name check already fails.)
- Wrong value written (e.g. `WARMUP_RATIO = 0.5`) — the corresponding hard-fact regex fails.
- Over-edit that changes `WARMDOWN_RATIO` away from `0.5` — not directly checked statically (residual ceiling: the evaluator concatenates edit `newString`s only, so a preservation anchor on an untouched line can't distinguish correct silence from silent damage). Flagged for a future evaluator upgrade that also ORs against the final on-disk file.
- Malformed `edit` args (wrong parameter names) — `call_schema_valid` fails.
