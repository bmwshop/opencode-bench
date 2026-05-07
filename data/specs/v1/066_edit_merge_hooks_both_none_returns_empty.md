# v1 #66 edit_merge_hooks_both_none_returns_empty

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> Modify the function `merge_hooks` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the `merge_hooks` helper declared at module scope inside `requests`. It merges two optional hook dictionaries. Today, when BOTH arguments are `None`, the first guard (`session_hooks is None`) wins and the function returns the still-`None` `request_hooks` -- callers that expect a dict-shaped result then have to defensively coerce `None`. With the well-known wart `request_hooks == {'response': []}` already documented in the docstring, the function deserves a parallel guard for the all-`None` case.
> 
> Behavior contract:
> 
> Modify the function `merge_hooks` (declared at module scope inside `requests`) so that the all-`None` case returns an empty mapping built from the `dict_class` argument rather than `None`:
> 
> - Calling `merge_hooks(None, None)` now returns `OrderedDict()` (the default `dict_class`); calling `merge_hooks(None, None, dict_class=dict)` would similarly return a plain `dict()`. The returned value is an instance of `OrderedDict` when `dict_class` is its default.
> - Existing behaviour on any non-`None` argument is preserved exactly: `merge_hooks({'response': ['a']}, None)` returns `{'response': ['a']}`; `merge_hooks(None, {'response': ['b']})` returns `{'response': ['b']}`; and the existing `request_hooks == {'response': []}` short-circuit still routes to `session_hooks` -- e.g. `merge_hooks({'response': []}, {'response': ['c']})` returns `{'response': ['c']}`.
> 
> The minimal change is a single new branch at the top of the function body that runs before the two existing `is None`-or-empty guards. Do NOT modify the existing two guards or the trailing `merge_setting(...)` call.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/sessions.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the function unchanged, so `merge_hooks(None, None)` still returns `None` and callers crash on a `.get('response')` they expected to be safe (`no-change`).
- Returns a plain `dict()` rather than `dict_class()`, so callers that relied on insertion order via `OrderedDict` see a different concrete type even though the equality comparison happens to pass (`partial-edit`).
- Adds the new branch but places it AFTER the two existing guards, where it can never fire because the first guard already returned `request_hooks` (which is `None`), so the all-`None` case still returns `None` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
