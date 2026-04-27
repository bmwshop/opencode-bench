# v1 #58 edit_default_hooks_include_request

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='extend-registry', scope_kind='single-file', answer_shape='value-equality', unique_trait='extend-module-level-hook-event-list'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `default_hooks` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/hooks.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `default_hooks` and its supporting module-level state (declared in the tiny hooks module of the `requests` package) so that the hook system supports a `'request'` event in addition to the existing `'response'` event:
> 
> - The module-level list of hook event names (currently exactly `['response']`) must become exactly `['response', 'request']`, in that order, with length `2`.
> - `default_hooks()` must continue to return a `dict` whose `'response'` key maps to `[]` (the empty list).
> - `default_hooks()` must additionally have a `'request'` key that maps to `[]`.
> - `len(default_hooks())` must equal exactly `2`.
> 
> The minimal change is to extend the module-level list and let the existing dict comprehension propagate the new key automatically. Do NOT hard-code the `'request'` key directly in the comprehension or append a non-empty default callback list.

## Ground truth (reference edit)

`src/requests/hooks.py` (oldString occurs exactly once in the baseline):

```python
# oldString
HOOKS = ["response"]


def default_hooks():
    return {event: [] for event in HOOKS}
```

```python
# newString
HOOKS = ["response", "request"]


def default_hooks():
    return {event: [] for event in HOOKS}
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `'response' in default_hooks()` |
| 2 | regression | over-edit | `default_hooks()['response'] == []` |
| 3 | new_behavior | no-change | `'request' in default_hooks()` |
| 4 | new_behavior | partial-edit | `default_hooks()['request'] == []` |
| 5 | new_behavior | partial-edit | `len(default_hooks()) == 2` |
| 6 | new_behavior | partial-edit | `'response' in HOOKS and 'request' in HOOKS and len(HOOKS) == 2` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def default_hooks` -> `src/requests/hooks.py`
- `default_hooks` -> `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`
- `HOOKS = ` -> `src/requests/hooks.py`

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

> Modify the function `default_hooks` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the tiny hooks module that declares the list of hook event names and the helper `default_hooks` that returns a default, empty hook registry. The file already defines a module-level list of supported hook names; the default hook registry is built as a dict comprehension over that list.
> 
> Behavior contract:
> 
> Modify the function `default_hooks` and its supporting module-level state (declared in the tiny hooks module of the `requests` package) so that the hook system supports a `'request'` event in addition to the existing `'response'` event:
> 
> - The module-level list of hook event names (currently exactly `['response']`) must become exactly `['response', 'request']`, in that order, with length `2`.
> - `default_hooks()` must continue to return a `dict` whose `'response'` key maps to `[]` (the empty list).
> - `default_hooks()` must additionally have a `'request'` key that maps to `[]`.
> - `len(default_hooks())` must equal exactly `2`.
> 
> The minimal change is to extend the module-level list and let the existing dict comprehension propagate the new key automatically. Do NOT hard-code the `'request'` key directly in the comprehension or append a non-empty default callback list.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/hooks.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `'response' in default_hooks()` (kind: regression)
- **over-edit**: caught by `default_hooks()['response'] == []` (kind: regression)
- **no-change**: caught by `'request' in default_hooks()` (kind: new_behavior)
- **partial-edit**: caught by `default_hooks()['request'] == []` (kind: new_behavior)
- **partial-edit**: caught by `len(default_hooks()) == 2` (kind: new_behavior)
- **partial-edit**: caught by `'response' in HOOKS and 'request' in HOOKS and len(HOOKS) == 2` (kind: new_behavior)

## Fail modes

- Leaves the module unchanged, so `'request' not in default_hooks()` (`no-change`).
- Adds `'request'` to the registry but as a non-empty list (e.g. a default callback), breaking the `== []` assert (`over-edit`).
- Adds `'request'` only to the returned dict via a hardcoded key, without updating the module-level list of hook names, so the new-behavior assert on the list fails (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
