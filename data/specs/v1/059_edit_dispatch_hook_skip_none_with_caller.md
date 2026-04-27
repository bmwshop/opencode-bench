# v1 #59 edit_dispatch_hook_skip_none_with_caller

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **hard**
- leak_function_name: **false**
- structural_signature: `template='cross-file-contract', scope_kind='multi-file', answer_shape='cross-file-pair', unique_trait='impl-skips-none-caller-validates-shape'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `dispatch_hook` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/hooks.py`, `src/requests/sessions.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level dispatcher (in the tiny hooks module of the package):
> 
> - Today, the dispatcher runs every registered callback for an event against a piece of data, returning the last non-`None` callback result. If the callback list contains a `None` entry the dispatcher crashes (calling `None(...)` raises `TypeError: 'NoneType' object is not callable`).
> - Tighten the dispatcher so a `None` entry in the callback list is silently skipped. Concretely: with `hook_data=10` and the callback list `[lambda d: d + 1]`, the dispatcher must still return `11`; with the same data and the list `[None, lambda d: d + 1]`, the dispatcher must now return `11` (the `None` entry is skipped); with `[None]` it must return `10`.
> - All existing behaviour is preserved exactly: with no hooks the data is returned unchanged; with a hooks dict of `None` or `{}` the data is returned unchanged; a single-callable hook value (not wrapped in a list) is still invoked; chained hooks still propagate the last non-`None` callback result.
> 
> Higher-level helper (in the sibling session module that already contains the existing top-level `merge_hooks` and `merge_setting` helpers):
> 
> - Add a NEW top-level helper named `apply_response_hooks(hooks, response)` that defends against malformed `hooks` arguments before delegating to the lower-level dispatcher. It must:
>   - Return `response` unchanged when `hooks` is `None`.
>   - Return `response` unchanged when `hooks` is not a `dict` (e.g. a list or any other non-dict value).
>   - Return `response` unchanged when `hooks` is a dict that does not contain the key `'response'`.
>   - Otherwise delegate to the lower-level dispatcher with the event key `'response'` (and return its result).
> - For example: `apply_response_hooks(None, 'r')` returns `'r'`; `apply_response_hooks({}, 'r')` returns `'r'`; and `apply_response_hooks({'response': [None, lambda d: d.upper()]}, 'hi')` returns `'HI'`.
> 
> Locate the lower-level dispatcher by searching the codebase for the docstring `Dispatches a hook` or for the callback-iteration loop; locate the sibling caller file by searching for the existing top-level `merge_hooks` helper.

## Ground truth (reference edit)

`src/requests/hooks.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def dispatch_hook(key, hooks, hook_data, **kwargs):
    """Dispatches a hook dictionary on a given piece of data."""
    hooks = hooks or {}
    hooks = hooks.get(key)
    if hooks:
        if hasattr(hooks, "__call__"):
            hooks = [hooks]
        for hook in hooks:
            _hook_data = hook(hook_data, **kwargs)
            if _hook_data is not None:
                hook_data = _hook_data
    return hook_data
```

```python
# newString
def dispatch_hook(key, hooks, hook_data, **kwargs):
    """Dispatches a hook dictionary on a given piece of data."""
    hooks = hooks or {}
    hooks = hooks.get(key)
    if hooks:
        if hasattr(hooks, "__call__"):
            hooks = [hooks]
        for hook in hooks:
            if hook is None:
                continue
            _hook_data = hook(hook_data, **kwargs)
            if _hook_data is not None:
                hook_data = _hook_data
    return hook_data
```

`src/requests/sessions.py` (oldString occurs exactly once in the baseline):

```python
# oldString
    return merge_setting(request_hooks, session_hooks, dict_class)


class SessionRedirectMixin:
```

```python
# newString
    return merge_setting(request_hooks, session_hooks, dict_class)


def apply_response_hooks(hooks, response):
    """Defensive wrapper for invoking the 'response' hook chain.

    Returns ``response`` unchanged when ``hooks`` is None, when ``hooks``
    is not a dict, or when the dict has no ``'response'`` key. Otherwise
    delegates to :func:`dispatch_hook` with the ``'response'`` event.
    """
    if hooks is None:
        return response
    if not isinstance(hooks, dict):
        return response
    if "response" not in hooks:
        return response
    return dispatch_hook("response", hooks, response)


class SessionRedirectMixin:
```


## Hidden truth table (graders only) (N = 10)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `dispatch_hook('response', {'response': [lambda d: d + 1]}, 10) == 11` |
| 2 | regression | over-edit | `dispatch_hook('response', {}, 10) == 10` |
| 3 | regression | over-edit | `dispatch_hook('response', None, 10) == 10` |
| 4 | regression | over-edit | `dispatch_hook('response', {'response': lambda d: d * 2}, 5) == 10` |
| 5 | new_behavior | no-change | `dispatch_hook('response', {'response': [None, lambda d: d + 1]}, 10) == 11` |
| 6 | new_behavior | partial-edit | `dispatch_hook('response', {'response': [None]}, 10) == 10` |
| 7 | new_behavior | no-change | `apply_response_hooks(None, 'r') == 'r'` |
| 8 | new_behavior | partial-edit | `apply_response_hooks({}, 'r') == 'r'` |
| 9 | new_behavior | partial-edit | `apply_response_hooks([1, 2, 3], 'r') == 'r'` |
| 10 | new_behavior | partial-edit | `apply_response_hooks({'response': [None, lambda d: d.upper()]}, 'hi') == 'HI'` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def dispatch_hook` -> `src/requests/hooks.py`
- `Dispatches a hook` -> `src/requests/hooks.py`
- `merge_hooks` -> `src/requests/sessions.py`

- Union (D = 2): `src/requests/hooks.py`, `src/requests/sessions.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> In this `requests` checkout, satisfy the cross-file behavior contract below. The change requires consistent edits in TWO related files inside `src/requests/`. Find the relevant files by searching the repo for the behavior described.
> 
> > The target spans two related files: a low-level hook dispatcher in the tiny hooks module, plus a defensive wrapper that the agent must add to the session module that already houses `merge_hooks` and `merge_setting`.
> 
> Behavior contract:
> 
> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level dispatcher (in the tiny hooks module of the package):
> 
> - Today, the dispatcher runs every registered callback for an event against a piece of data, returning the last non-`None` callback result. If the callback list contains a `None` entry the dispatcher crashes (calling `None(...)` raises `TypeError: 'NoneType' object is not callable`).
> - Tighten the dispatcher so a `None` entry in the callback list is silently skipped. Concretely: with `hook_data=10` and the callback list `[lambda d: d + 1]`, the dispatcher must still return `11`; with the same data and the list `[None, lambda d: d + 1]`, the dispatcher must now return `11` (the `None` entry is skipped); with `[None]` it must return `10`.
> - All existing behaviour is preserved exactly: with no hooks the data is returned unchanged; with a hooks dict of `None` or `{}` the data is returned unchanged; a single-callable hook value (not wrapped in a list) is still invoked; chained hooks still propagate the last non-`None` callback result.
> 
> Higher-level helper (in the sibling session module that already contains the existing top-level `merge_hooks` and `merge_setting` helpers):
> 
> - Add a NEW top-level helper named `apply_response_hooks(hooks, response)` that defends against malformed `hooks` arguments before delegating to the lower-level dispatcher. It must:
>   - Return `response` unchanged when `hooks` is `None`.
>   - Return `response` unchanged when `hooks` is not a `dict` (e.g. a list or any other non-dict value).
>   - Return `response` unchanged when `hooks` is a dict that does not contain the key `'response'`.
>   - Otherwise delegate to the lower-level dispatcher with the event key `'response'` (and return its result).
> - For example: `apply_response_hooks(None, 'r')` returns `'r'`; `apply_response_hooks({}, 'r')` returns `'r'`; and `apply_response_hooks({'response': [None, lambda d: d.upper()]}, 'hi')` returns `'HI'`.
> 
> Locate the lower-level dispatcher by searching the codebase for the docstring `Dispatches a hook` or for the callback-iteration loop; locate the sibling caller file by searching for the existing top-level `merge_hooks` helper.
> 
> Constraints:
> - Edit exactly TWO files inside `src/requests/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/hooks.py`, `src/requests/sessions.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `dispatch_hook('response', {'response': [lambda d: d + 1]}, 10) == 11` (kind: regression)
- **over-edit**: caught by `dispatch_hook('response', {}, 10) == 10` (kind: regression)
- **over-edit**: caught by `dispatch_hook('response', None, 10) == 10` (kind: regression)
- **over-edit**: caught by `dispatch_hook('response', {'response': lambda d: d * 2}, 5) == 10` (kind: regression)
- **no-change**: caught by `dispatch_hook('response', {'response': [None, lambda d: d + 1]}, 10) == 11` (kind: new_behavior)
- **partial-edit**: caught by `dispatch_hook('response', {'response': [None]}, 10) == 10` (kind: new_behavior)
- **no-change**: caught by `apply_response_hooks(None, 'r') == 'r'` (kind: new_behavior)
- **partial-edit**: caught by `apply_response_hooks({}, 'r') == 'r'` (kind: new_behavior)
- **partial-edit**: caught by `apply_response_hooks([1, 2, 3], 'r') == 'r'` (kind: new_behavior)
- **partial-edit**: caught by `apply_response_hooks({'response': [None, lambda d: d.upper()]}, 'hi') == 'HI'` (kind: new_behavior)

## Fail modes

- Edits only the lower-level dispatcher (skips `None` entries) but never adds the new sibling helper, so the new-behavior asserts on `apply_response_hooks` fail (`partial-edit`).
- Adds the sibling helper but doesn't touch the dispatcher, so a `None` entry in a callback list still crashes the dispatcher (`partial-edit`).
- Replaces the callback list with `[h for h in hooks if h]`, which also drops other falsy callbacks instead of just `None` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
