# v1 #7 delegate_schedule_audit

## Category

subagent

## Contract

routing

## Surface

subagents

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Delegation / orchestration atomic skill (per Ma et al. arXiv:2604.05013, generalized to multi-agent): the parent agent must route the reading work to an `explore` subagent via the `task` tool, then faithfully persist the subagent's findings to disk. Tests two things end-to-end — parent-side delegation discipline (the parent doesn't bypass the subagent) and result correctness (the on-disk `audit.md` contains the canonical `FACTS:` line).

Content validation uses a **single anchored exact-match regex** on a canonical `FACTS:` line in `audit.md`. The pattern encodes four ground-truth facts from `train.py`: `WARMUP_RATIO=0.0`, `WARMDOWN_RATIO=0.5`, `FINAL_LR_FRAC=0.0`, and `consumer=get_lr_multiplier`. This design (a) simplifies the content-check surface to one check instead of four name-presence regexes, and (b) upgrades from presence-testing ("did the model mention these names?") to correctness-testing ("did the model actually know their values?") — a hallucinated summary that uses standard-looking defaults cannot satisfy the regex. `file_regex_disk` uses `re.MULTILINE` so `^...$` correctly anchor to line boundaries.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. `audit.md` does not pre-exist. The `explore` subagent is read-only by design (its configured tools deny `write`/`edit`), so the parent must perform the `write` itself to persist `audit.md`.

## Prompt

> Hand off the reading to an explore subagent: have it open train.py and summarize how the LR schedule is computed -- the three ratio constants, the function that consumes them, and where that function is called. Then write the returned summary to audit.md at the repo root, and make sure audit.md ends with this exact line with values filled in from the actual file:
>
> FACTS: WARMUP_RATIO=<v> WARMDOWN_RATIO=<v> FINAL_LR_FRAC=<v> consumer=<function_name>
>
> Do not read any files yourself; only the subagent reads.

## Pass criteria (5 checks)

1. `any_tool_name` `task` — parent must delegate via the `task` tool.
2. `any_tool_param_value` tool=`task` param=`subagent_type` equals `explore` — delegation must target the `explore` subagent specifically, not some other subagent type.
3. `no_tool_name` not `[read, grep, glob, bash]` — parent-only guard, consolidated into a single check against a list of filesystem-reading tools. Parent-only (not `_recursive`) is intentional: the subagent is allowed (and required) to call `read`. `bash` is included so the parent can't shell out (`cat`, `head`) to bypass the guard.
4. `file_regex_disk` `audit.md` `^FACTS: WARMUP_RATIO=0\.0 WARMDOWN_RATIO=0\.5 FINAL_LR_FRAC=0\.0 consumer=get_lr_multiplier$` — **the sole content assertion**: a single anchored regex encoding all four ground-truth facts in a canonical exact-match line. Pass iff `audit.md` contains this exact line (bounded by `^` and `$` per `re.MULTILINE`).
5. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

Note: previous revisions included `any_tool_name_recursive` checks for `read` and `write`. Both are redundant with the on-disk assertion: if the subagent never `read`, the values in `audit.md` would be hallucinated and fail check 4; if nothing ever `write`s `audit.md`, check 4 can't match because the file doesn't exist. We prefer results-oriented validation over tool-trajectory bookkeeping whenever the result anchor is strict enough to subsume it.

## Shortest path

**2 tool calls**: one `task` (delegating the read+summarize job to an `explore` subagent, which internally performs at least one `read` on `train.py`) + one `write` (parent persists the subagent-returned summary plus the canonical `FACTS:` trailer line to `audit.md`).

## Fail modes

- Parent reads the file itself (`read`/`grep`/`glob`/`bash cat`) — check 3 fails. A clean alternative path that skips delegation also fails check 1.
- Parent delegates to the wrong subagent type (e.g., `general`) — check 2 fails.
- Parent writes nothing / `audit.md` is missing — check 4 fails because the file isn't on disk.
- Parent writes `audit.md` but the `FACTS:` line is malformed (wrong values, wrong separators, missing `consumer=`, extra trailing whitespace that breaks the `$` anchor) — check 4 fails. This is also what fails when the subagent hallucinated the values without actually reading.
- Malformed `task` / `write` args — `call_schema_valid` fails.
