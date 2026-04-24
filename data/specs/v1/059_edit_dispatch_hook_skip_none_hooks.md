# v1 #59 edit_dispatch_hook_skip_none_hooks

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `dispatch_hook` (plus in-file callees: _(none)_)
- Target file: `src/requests/hooks.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/hooks.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

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

## Truth table (N = 7)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `dispatch_hook('response', {'response': [lambda d: d + 1]}, 10) == 11` |
| 2 | regression | over-edit | `dispatch_hook('response', {}, 10) == 10` |
| 3 | regression | over-edit | `dispatch_hook('response', None, 10) == 10` |
| 4 | regression | over-edit | `dispatch_hook('response', {'response': lambda d: d * 2}, 5) == 10` |
| 5 | new_behavior | no-change | `dispatch_hook('response', {'response': [None, lambda d: d + 1]}, 10) == 11` |
| 6 | new_behavior | partial-edit | `dispatch_hook('response', {'response': [None]}, 10) == 10` |
| 7 | new_behavior | partial-edit | `dispatch_hook('response', {'response': [lambda d: d + 1, None, lambda d: d * 2]}, 10) == 22` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def dispatch_hook` -> `src/requests/hooks.py`
- `dispatch_hook` -> `src/requests/hooks.py`, `src/requests/sessions.py`
- `hook` -> `src/requests/auth.py`, `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`
- `hook_data|hooks\[` -> `src/requests/hooks.py`, `src/requests/models.py`

- Union (D = 4): `src/requests/auth.py`, `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`dispatch_hook`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `dispatch_hook` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the hook-dispatch utility that runs every registered callback for a given event against a piece of data, using a callback's return value (if not `None`) as the new data. It lives in the tiny hooks module of the `requests` package.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert dispatch_hook('response', {'response': [lambda d: d + 1]}, 10) == 11
>     assert dispatch_hook('response', {}, 10) == 10
>     assert dispatch_hook('response', None, 10) == 10
>     assert dispatch_hook('response', {'response': lambda d: d * 2}, 5) == 10
>     assert dispatch_hook('response', {'response': [None, lambda d: d + 1]}, 10) == 11
>     assert dispatch_hook('response', {'response': [None]}, 10) == 10
>     assert dispatch_hook('response', {'response': [lambda d: d + 1, None, lambda d: d * 2]}, 10) == 22
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every regression assert; do not delete existing behavior.
> - Use the exact exception class names that appear in the assertions above (e.g. `ValueError`, `TypeError`) -- other classes will not satisfy the asserts.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` `src/requests/hooks.py` - every entry in the truth table above evaluates True against the patched file (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `dispatch_hook('response', {'response': [lambda d: d + 1]}, 10) == 11` (kind: regression)
- **over-edit**: caught by `dispatch_hook('response', {}, 10) == 10` (kind: regression)
- **over-edit**: caught by `dispatch_hook('response', None, 10) == 10` (kind: regression)
- **over-edit**: caught by `dispatch_hook('response', {'response': lambda d: d * 2}, 5) == 10` (kind: regression)
- **no-change**: caught by `dispatch_hook('response', {'response': [None, lambda d: d + 1]}, 10) == 11` (kind: new_behavior)
- **partial-edit**: caught by `dispatch_hook('response', {'response': [None]}, 10) == 10` (kind: new_behavior)
- **partial-edit**: caught by `dispatch_hook('response', {'response': [lambda d: d + 1, None, lambda d: d * 2]}, 10) == 22` (kind: new_behavior)

## Fail modes

- Leaves the loop unchanged, so a `None` entry in the hook list raises `TypeError: 'NoneType' object is not callable` (`no-change`).
- Skips the entire callback list when any `None` is present (e.g. `if None in hooks: return hook_data`), breaking the mixed-list regression (`over-edit`).
- Skips `None` only in the list-path but not the single-callable path; still fine because the single-callable path never sees `None` -- but a naive fix that converts hooks to `[h for h in hooks if h]` also drops other falsy callbacks (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
