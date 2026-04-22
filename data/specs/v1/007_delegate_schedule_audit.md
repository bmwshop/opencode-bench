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

Delegation / orchestration atomic skill (per Ma et al. arXiv:2604.05013, generalized to multi-agent): the parent agent must route the reading work to an `explore` subagent via the `task` tool, then faithfully persist the subagent's findings to disk. Tests the full recursive-verifier stack end-to-end — parent-only negative guards, recursive positive guards on subagent tool use, and layer-agnostic file-content checks on the parent's final write.

Content validation uses a **single anchored exact-match regex** on a canonical `FACTS:` line in `audit.md`. The pattern encodes four ground-truth facts from `train.py`: `WARMUP_RATIO=0.0`, `WARMDOWN_RATIO=0.5`, `FINAL_LR_FRAC=0.0`, and `consumer=get_lr_multiplier`. This design (a) simplifies the content-check surface to one check instead of four name-presence regexes, and (b) upgrades from presence-testing ("did the model mention these names?") to correctness-testing ("did the model actually know their values?") — a hallucinated summary that uses standard-looking defaults cannot satisfy the regex. `file_regex` uses `re.MULTILINE` so `^...$` correctly anchor to line boundaries.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. `audit.md` does not pre-exist. The `explore` subagent is read-only by design, so the parent must perform the `write` itself — this naturally satisfies the `any_tool_name_recursive: write` check without any special scaffolding.

## Prompt

> Hand off the reading to an explore subagent: have it open train.py and summarize how the LR schedule is computed -- the three ratio constants, the function that consumes them, and where that function is called. Then write the returned summary to audit.md at the repo root, and make sure audit.md ends with this exact line with values filled in from the actual file:
>
> FACTS: WARMUP_RATIO=<v> WARMDOWN_RATIO=<v> FINAL_LR_FRAC=<v> consumer=<function_name>
>
> Do not read any files yourself; only the subagent reads.

## Pass criteria (9 checks)

1. `any_tool_name` `task` — parent must delegate via the `task` tool.
2. `any_tool_param_value` tool=`task` param=`subagent_type` equals `explore` — delegation must target the `explore` subagent specifically, not some other subagent type.
3. `no_tool_name` not `read` — parent-only guard: the parent must not call `read` directly. Parent-only (not `_recursive`) is intentional — the subagent is allowed (and required) to call `read`.
4. `no_tool_name` not `grep` — parent-only guard.
5. `no_tool_name` not `glob` — parent-only guard. (The three parent-only negative guards are kept separate because the registry's `no_tool_name` does not accept a list.)
6. `any_tool_name_recursive` `read` — somewhere in the parent+subagent trajectory, `read` must have been called. Combined with guards 3-5, this forces the read to happen inside the subagent.
7. `any_tool_name_recursive` `write` — the summary must be persisted (parent satisfies this when writing `audit.md`).
8. `file_regex` `audit.md` `^FACTS: WARMUP_RATIO=0\.0 WARMDOWN_RATIO=0\.5 FINAL_LR_FRAC=0\.0 consumer=get_lr_multiplier$` — **the sole content assertion**: a single anchored regex encoding all four ground-truth facts in a canonical exact-match line. Pass iff `audit.md` contains this exact line (bounded by `^` and `$` per `re.MULTILINE`).
9. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**2 tool calls**: one `task` (delegating the read+summarize job to an `explore` subagent, which internally performs at least one `read` on `train.py`) + one `write` (parent persists the subagent-returned summary plus the canonical `FACTS:` trailer line to `audit.md`).

## Fail modes

- Parent reads `train.py` directly — fails checks 3-5 (parent-only negative guards). A clean alternative path that skips delegation also fails check 1 (`task` not invoked).
- Parent delegates to the wrong subagent type (e.g., `general`) — check 2 fails.
- Parent delegates but the subagent never reads (e.g., subagent answers from prior knowledge) — check 6 fails.
- Parent delegates and reads cleanly but forgets to write `audit.md` — check 7 fails.
- Parent writes `audit.md` but the `FACTS:` line is malformed (wrong values, wrong separators, missing `consumer=`, extra trailing whitespace that breaks the `$` anchor) — check 8 fails. This is also what fails when the subagent hallucinated the values without actually reading.
- Malformed `task` / `write` args — `call_schema_valid` fails.
