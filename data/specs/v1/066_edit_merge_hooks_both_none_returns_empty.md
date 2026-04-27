# v1 #66 edit_merge_hooks_both_none_returns_empty

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='null-tolerant-merge', scope_kind='single-file', answer_shape='value-equality', unique_trait='both-none-returns-empty-dict-class-instead-of-none'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `merge_hooks` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/sessions.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `merge_hooks` (declared at module scope inside `requests`) so that the all-`None` case returns an empty mapping built from the `dict_class` argument rather than `None`:
> 
> - Calling `merge_hooks(None, None)` now returns `OrderedDict()` (the default `dict_class`); calling `merge_hooks(None, None, dict_class=dict)` would similarly return a plain `dict()`. The returned value is an instance of `OrderedDict` when `dict_class` is its default.
> - Existing behaviour on any non-`None` argument is preserved exactly: `merge_hooks({'response': ['a']}, None)` returns `{'response': ['a']}`; `merge_hooks(None, {'response': ['b']})` returns `{'response': ['b']}`; and the existing `request_hooks == {'response': []}` short-circuit still routes to `session_hooks` -- e.g. `merge_hooks({'response': []}, {'response': ['c']})` returns `{'response': ['c']}`.
> 
> The minimal change is a single new branch at the top of the function body that runs before the two existing `is None`-or-empty guards. Do NOT modify the existing two guards or the trailing `merge_setting(...)` call.

## Ground truth (reference edit)

`src/requests/sessions.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    """Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.
    """
    if session_hooks is None or session_hooks.get("response") == []:
        return request_hooks

    if request_hooks is None or request_hooks.get("response") == []:
        return session_hooks

    return merge_setting(request_hooks, session_hooks, dict_class)
```

```python
# newString
def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    """Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.
    """
    if request_hooks is None and session_hooks is None:
        return dict_class()

    if session_hooks is None or session_hooks.get("response") == []:
        return request_hooks

    if request_hooks is None or request_hooks.get("response") == []:
        return session_hooks

    return merge_setting(request_hooks, session_hooks, dict_class)
```


## Hidden truth table (graders only) (N = 5)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `merge_hooks({'response': ['a']}, None) == {'response': ['a']}` |
| 2 | regression | over-edit | `merge_hooks(None, {'response': ['b']}) == {'response': ['b']}` |
| 3 | regression | over-edit | `merge_hooks({'response': []}, {'response': ['c']}) == {'response': ['c']}` |
| 4 | new_behavior | no-change | `merge_hooks(None, None) == OrderedDict()` |
| 5 | new_behavior | partial-edit | `isinstance(merge_hooks(None, None), OrderedDict)` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def merge_hooks` -> `src/requests/sessions.py`
- `default_hooks` -> `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`
- `session_hooks` -> `src/requests/sessions.py`

- Union (D = 3): `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

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

1. `exec_assert` (`src/requests/sessions.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `merge_hooks({'response': ['a']}, None) == {'response': ['a']}` (kind: regression)
- **over-edit**: caught by `merge_hooks(None, {'response': ['b']}) == {'response': ['b']}` (kind: regression)
- **over-edit**: caught by `merge_hooks({'response': []}, {'response': ['c']}) == {'response': ['c']}` (kind: regression)
- **no-change**: caught by `merge_hooks(None, None) == OrderedDict()` (kind: new_behavior)
- **partial-edit**: caught by `isinstance(merge_hooks(None, None), OrderedDict)` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `merge_hooks(None, None)` still returns `None` and callers crash on a `.get('response')` they expected to be safe (`no-change`).
- Returns a plain `dict()` rather than `dict_class()`, so callers that relied on insertion order via `OrderedDict` see a different concrete type even though the equality comparison happens to pass (`partial-edit`).
- Adds the new branch but places it AFTER the two existing guards, where it can never fire because the first guard already returned `request_hooks` (which is `None`), so the all-`None` case still returns `None` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
