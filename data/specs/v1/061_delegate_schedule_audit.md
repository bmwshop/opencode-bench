# v1 #61 delegate_schedule_audit

## Category

subagent

## Contract

completion

## Surface

subagents

## Repo

`autoresearch` — karpathy/autoresearch, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/autoresearch/`.

## Capability

Delegation / orchestration atomic skill (per Ma et al. arXiv:2604.05013, generalized to multi-agent): the parent agent must route the reading work to an `explore` subagent via the `task` tool, then faithfully persist the subagent's findings to disk. Tests two things end-to-end — parent-side delegation discipline (the parent doesn't bypass the subagent) and result correctness (the on-disk `audit.py` exposes the canonical facts as module-level constants).

Content validation uses `exec_assert` on a Python facts file `audit.py`, evaluating five independent equality assertions against `ast.literal_eval`-extracted constants. The audit subject is the optimizer-LR block in `train.py` (`EMBEDDING_LR`, `UNEMBEDDING_LR`, `MATRIX_LR`, `WEIGHT_DECAY`) plus the consumer method name — disjoint from the constants exercised by #11 (edits the LR-schedule ratios) and #13 (imports `get_lr_multiplier` and probes schedule values), so a model that passed those cannot coast on in-context facts. The unusual numerics (`UNEMBEDDING_LR = 0.004`, `MATRIX_LR = 0.04`) mean hallucinated round defaults fail cleanly, and the consumer (`setup_optimizer`) is a class method rather than a top-level function, forcing the subagent to do real class-member reading.

## Setup

The per-run fixture is a pinned copy of `karpathy/autoresearch`. `audit.py` does not pre-exist. The `explore` subagent is read-only by design (its configured tools deny `write`/`edit`), so the parent must perform the `write` itself to persist `audit.py`.

## Prompt

> Hand off the reading to an explore subagent: have it open train.py and identify the four optimizer learning-rate / weight-decay constants (EMBEDDING_LR, UNEMBEDDING_LR, MATRIX_LR, WEIGHT_DECAY) and the function that consumes them. Then write audit.py at the repo root containing exactly these five module-level constants, with values filled in from the actual file:
>
> EMBEDDING_LR = \<v\>
> UNEMBEDDING_LR = \<v\>
> MATRIX_LR = \<v\>
> WEIGHT_DECAY = \<v\>
> CONSUMER = "\<function_name\>"
>
> Do not read any files yourself; only the subagent reads.

## Pass criteria (5 checks)

1. `any_tool_name` `task` — parent must delegate via the `task` tool.
2. `any_tool_param_value` tool=`task` param=`subagent_type` equals `explore` — delegation must target the `explore` subagent specifically, not some other subagent type.
3. `no_tool_name` not `[read, grep, glob, bash]` — parent-only guard, consolidated into a single check against a list of filesystem-reading tools. Parent-only (not `_recursive`) is intentional: the subagent is allowed (and required) to call `read`. `bash` is included so the parent can't shell out (`cat`, `head`) to bypass the guard.
4. `exec_assert` on `audit.py` with constants `[EMBEDDING_LR, UNEMBEDDING_LR, MATRIX_LR, WEIGHT_DECAY, CONSUMER]` and five assertions:
   - `EMBEDDING_LR == 0.6` — pinned from [`train.py`](../../../projects/v1/autoresearch/train.py) line 439.
   - `UNEMBEDDING_LR == 0.004` — line 440; the unusual value (not `0.001`) defeats round-default hallucination.
   - `MATRIX_LR == 0.04` — line 441; same defense against guessing `0.01`.
   - `WEIGHT_DECAY == 0.2` — line 443.
   - `CONSUMER == 'setup_optimizer'` — the `GPT` method at line 236 that is invoked with all four constants as kwargs at line 499.

   Each assertion reports a distinct failure reason, so a partially-correct audit (e.g. right values, wrong consumer, or three right LRs and one hallucinated one) surfaces the exact offending fact rather than a single binary miss.
5. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas.

Note: previous revisions included `any_tool_name_recursive` checks for `read` and `write`. Both are redundant with the on-disk assertion: if the subagent never `read`, the values in `audit.py` would be hallucinated and fail check 4; if nothing ever `write`s `audit.py`, check 4 reports `file not found`. We prefer results-oriented validation over tool-trajectory bookkeeping whenever the result anchor is strict enough to subsume it.

## Shortest path

**2 tool calls**: one `task` (delegating the read+summarize job to an `explore` subagent, which internally performs at least one `read` on `train.py`) + one `write` (parent persists `audit.py` containing the five module-level constants).

## Fail modes

- Parent reads the file itself (`read`/`grep`/`glob`/`bash cat`) — check 3 fails. A clean alternative path that skips delegation also fails check 1.
- Parent delegates to the wrong subagent type (e.g., `general`) — check 2 fails.
- Parent writes nothing / `audit.py` missing — `exec_assert` reports `file not found: .../audit.py` and check 4 fails.
- Parent writes `audit.py` but omits a required name (e.g., forgets `CONSUMER`) — `exec_assert` reports `constant 'CONSUMER' not found`.
- Parent writes `audit.py` but one or more values are hallucinated (e.g., `UNEMBEDDING_LR = 0.001`) — `exec_assert` reports the specific `assert failed: UNEMBEDDING_LR == 0.004`.
- Parent uses a non-literal RHS (e.g., `EMBEDDING_LR = float(os.environ["LR"])`) — `exec_assert` reports `constant 'EMBEDDING_LR' not a literal: ...`.
- Parent produces invalid Python — `exec_assert` reports `SyntaxError at line N: ...`.
- Malformed `task` / `write` args — `call_schema_valid` fails.
