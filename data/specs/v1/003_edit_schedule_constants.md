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

## Pass criteria (3 checks)

1. `file_regex_disk` `train.py` `WARMUP_RATIO\s*=\s*0\.05\b` — hard fact: the new warmup value is exactly `0.05`.
2. `file_regex_disk` `train.py` `FINAL_LR_FRAC\s*=\s*0\.1\b` — hard fact: the new final-LR fraction is exactly `0.1`.
3. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

Note on anchor design: these use `file_regex_disk`, which reads the final on-disk file at `_project_dir / path` and applies the regex with `re.MULTILINE`. A `\b` terminator on each numeric literal prevents `0.05` from matching `0.050` / `0.1` from matching `0.10`. A WARMDOWN preservation anchor (e.g. `WARMDOWN_RATIO\s*=\s*0\.5\b`) is now viable under `file_regex_disk` because the disk read sees the full unchanged file; it is not added in this revision, but is tracked as a future anchor-strength upgrade.

### Dropped: `any_tool_name_recursive: edit`

The tool-name check was removed in favor of pure results-oriented scoring. Rationale: the two hard-fact disk anchors already verify the outcome (the file on disk contains the correct numeric literals). *How* the model got there — `edit` tool, `write` tool, or even `bash sed -i` — is operationally uninteresting when the end state is correct. Keeping the anchor only penalized valid alternative paths without adding correctness signal. `call_schema_valid` remains to catch malformed tool arguments on any path actually taken.

## Shortest path

**2 tool calls**: one `read` on `train.py` to locate the constants, one `edit` to apply both value changes (opencode's `edit` tool accepts multiple replacements per call via repeated `oldString`/`newString` pairs, so a single edit can update both lines). A model that already knows the file layout can skip the read and do just one `edit`, in which case the `min_calls: 2` floor is the only gate.

## Fail modes

- Wrong value written (e.g. `WARMUP_RATIO = 0.5`) — the corresponding hard-fact regex fails.
- Model never modified the file (e.g. stopped mid-turn, answered conversationally) — both hard-fact regexes fail because the disk state still has the original `0.0` values.
- Over-edit that changes `WARMDOWN_RATIO` away from `0.5` — not directly checked in this revision, but now trivially addable via a `file_regex_disk` anchor on `WARMDOWN_RATIO\s*=\s*0\.5\b` because the evaluator reads final disk state.
- Malformed tool args on whatever path was taken — `call_schema_valid` fails.
