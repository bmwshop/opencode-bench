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

## Pass criteria (7 checks)

1. `no_tool_name` not `[edit, bash, write]` — plan-mode read-only constraint, consolidated into a single list-form guard.
2. `text_contains` `(?i)retry[-\s]?after` — plan names the target header.
3. `text_contains` `429` — plan names the target status code.
4. `text_contains` `Session|HTTPAdapter` — plan names the target class (case-sensitive: the bare lowercase `adapter` alternation was dropped because it matched generic "adapter pattern" prose; `Session` and `HTTPAdapter` are the actual class names).
5. `text_contains` `sessions\.py` — plan references the exact `sessions.py` filename. Catches the common `session.py` typo/hallucination (observed on nemotron-nano's `01-49-18` run, which answered from prior knowledge without calling any tools).
6. `text_contains` `adapters\.py` — plan references the exact `adapters.py` filename. Split from check 5 (previously a single OR anchor `sessions\.py|adapters\.py`) so a plan must name **both** files, not one or the other.
7. `call_schema_valid` — every tool call in the trace matches opencode's canonical JSON schemas (guards against malformed args on `read`/`grep`/`glob`).

## Shortest path

**2 tool calls**: read `src/requests/sessions.py`, read `src/requests/adapters.py`, then synthesize. A model answering from prior knowledge can probably hit checks 2–4 but is unlikely to hit both checks 5 and 6 without reading the package (getting both filenames exactly right including the plural `sessions` is the main source-grounding signal).

## Fail modes

- Uses `edit`/`write`/`bash` — violates plan-mode read-only constraint (check 1, single consolidated fail).
- Plan never names `Retry-After` or `429` — doesn't address the actual task.
- Plan says "adapter" generically but never names `Session` or `HTTPAdapter` by their exact class names — check 4 fails under the case-sensitive tightening.
- Plan hallucinates `session.py` (singular) — check 5 fails. Previously passed under the OR-form filename anchor because `adapters.py` was also mentioned.
- Plan names only `sessions.py` or only `adapters.py` — the unnamed file's check fails. Previously passed under the OR-form.
- Any `read`/`grep`/`glob` call uses the wrong argument shape (e.g. `path` instead of `filePath`) — `call_schema_valid` fails.

## Intentionally *not* checked

- **`any_tool_name: read`** — we don't require a specific `read` call. A model that navigates via `grep`/`glob` or reads the file through some other path still counts. The source-grounding signal comes from the text anchors (checks 4, 5, 6) being strict enough that prior-knowledge plans are unlikely to pass all three — especially the exact `sessions.py` filename, which the observed hallucination pattern misses.
- **"Which tests to add" anchor** — the prompt's `Include:` list mentions tests, but a text anchor for `(?i)test_|tests/` was considered and skipped to keep the check set focused on source-grounding signals. Can be added later if plans-without-tests becomes an observed gap.
