# v1 #2 plan_retry_after

## Category

plan_mode

## Contract

routing

## Surface

modes

## Repo

`requests` — psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Capability

Plan-mode read-only adherence against a widely-known, layered codebase. Today, requests delegates transport-level retries to urllib3's `Retry` via `HTTPAdapter`, but there is no first-class Session-level honoring of the HTTP 429 `Retry-After` header — a well-known real-world gap. Producing a concrete plan requires the model to read at least `src/requests/sessions.py` (the `Session.send` loop) and `src/requests/adapters.py` (`HTTPAdapter.send`), and to identify the right insertion point and configuration surface.

## Setup

The per-run fixture is a pinned copy of `psf/requests`. Relevant sources live under `src/requests/`; tests live under `tests/`.

## Prompt (run with `--agent plan`)

> Read the code in src/requests/ (Session and HTTPAdapter in particular) and produce a detailed, ordered plan for adding automatic handling of HTTP 429 responses that honors the Retry-After header at the Session level. Include: which file(s), class(es), and method(s) to change; where the retry loop lives today; how to make the new behavior configurable with a sensible default; which tests to add. Do not edit any files.

## Pass criteria (8 checks)

1. `no_tool_name` not `edit` — respects plan-mode read-only constraint
2. `no_tool_name` not `write` — no files may be created
3. `no_tool_name` not `bash` — no system-modifying commands
4. `text_contains` `(?i)retry[-\s]?after` — plan names the target header
5. `text_contains` `429` — plan names the target status code
6. `text_contains` `(?i)(session|httpadapter|adapter)` — plan identifies the architectural layer
7. `text_contains` `sessions\.py|adapters\.py` — plan references a specific source file (requires having actually read the package)
8. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas (guards against malformed args on `read`/`grep`/`glob`)

## Shortest path

**2 tool calls**: read `src/requests/sessions.py`, read `src/requests/adapters.py`, then synthesize. A model answering from prior knowledge can probably hit checks 4–6 but is unlikely to hit check 7 without reading the code.

## Fail modes

- Uses `edit`/`write`/`bash` — violates plan-mode read-only constraint.
- Plan never names `Retry-After` or `429` — doesn't address the actual task.
- Plan is architecture-free (no mention of Session / HTTPAdapter / specific source files) — model skipped reading the package.
- Any `read`/`grep`/`glob` call uses the wrong argument shape (e.g. `path` instead of `filePath`) — `call_schema_valid` fails.
