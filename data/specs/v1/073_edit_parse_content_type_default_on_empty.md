# v1 #73 edit_parse_content_type_default_on_empty

## Category

code_editing

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `src/requests/`; find it by searching the repo for the behavior described.
> 
> > The target is the small private helper inside `requests` that splits a `Content-Type` header value on `;`, returns the leading content-type token and a dict of parameters (e.g. `charset`, `boundary`). Today, when the header has no leading content-type token (it starts with a `;`, leaving `tokens[0]` as `''`), the helper returns an empty string for the content-type. Downstream consumers like `get_encoding_from_headers` then test substrings (`'text' in content_type`) against the empty string and produce confusing fallback behaviour.
> 
> Behavior contract:
> 
> In this `requests` checkout, the small private helper that parses a `Content-Type` header byte string into a `(content_type, params_dict)` tuple returns the empty string `''` for the content-type whenever the header starts with a `;` (so that the leading `;`-split token is empty). Downstream code like `get_encoding_from_headers` then tests `'text' in content_type`, which matches `''` only via fallback heuristics that are clearly wrong. Tighten the helper so that:
> 
> - When the leading content-type token would otherwise be the empty string, the helper returns `'application/octet-stream'` as the content-type instead. For example, parsing `;charset=utf-8` returns `('application/octet-stream', {'charset': 'utf-8'})`.
> - The params dict still parses normally for the leading-`;` case: parsing `;charset=utf-8` still produces `{'charset': 'utf-8'}`.
> - Existing behaviour on inputs that have a leading content-type is preserved exactly: parsing `text/html` returns `('text/html', {})`; parsing `text/html; charset=utf-8` produces `'text/html'` plus a `{'charset': 'utf-8'}` dict; parsing `application/json; charset="utf-8"; boundary=abc` produces `'application/json'` plus a `{'charset': 'utf-8', 'boundary': 'abc'}` dict (existing surrounding-quote stripping still applies); and a bare `application/octet-stream` (no params) returns `('application/octet-stream', {})`.
> 
> The minimal change is a single guard inserted between the `tokens[0].strip()` line and the `params_dict = {}` line that reassigns `content_type` to `'application/octet-stream'` when it is otherwise the empty string. Do NOT modify the parameter-parsing loop or its `strip_chars` handling. The helper lives among the small header-parsing helpers under `src/requests/`; locate it by searching for `content_type` or `charset` references in the codebase.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so a leading-`;` input still produces an empty-string content-type that pollutes downstream encoding detection (`no-change`).
- Replaces the empty content-type with the wrong default (e.g. `'text/plain'`), satisfying the leading-`;` case but accidentally also matching the `'text' in content_type` heuristic in `get_encoding_from_headers` and over-applying the `ISO-8859-1` fallback (`partial-edit`).
- Always overwrites the content-type with `'application/octet-stream'` (not just when it would be empty), so a valid `text/html` input now also returns `'application/octet-stream'` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
