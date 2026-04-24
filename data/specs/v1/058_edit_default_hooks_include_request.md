# v1 #58 edit_default_hooks_include_request

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `default_hooks` (plus in-file callees: _(none)_)
- Target file: `src/requests/hooks.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/hooks.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

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

## Truth table (N = 6)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `'response' in default_hooks()` |
| 2 | regression | over-edit | `default_hooks()['response'] == []` |
| 3 | new_behavior | no-change | `'request' in default_hooks()` |
| 4 | new_behavior | partial-edit | `default_hooks()['request'] == []` |
| 5 | new_behavior | partial-edit | `len(default_hooks()) == 2` |
| 6 | new_behavior | partial-edit | `'response' in HOOKS and 'request' in HOOKS and len(HOOKS) == 2` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def default_hooks` -> `src/requests/hooks.py`
- `default_hooks|HOOKS` -> `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`
- `hook` -> `src/requests/auth.py`, `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`
- `response.*event|event.*hook` -> `src/requests/models.py`

- Union (D = 4): `src/requests/auth.py`, `src/requests/hooks.py`, `src/requests/models.py`, `src/requests/sessions.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`default_hooks`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `default_hooks` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function. The module also defines the top-level name(s) `HOOKS`; you may need to update them as well.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target is the tiny hooks module that declares the list of hook event names and returns a default, empty hook registry. The file already defines a module-level list of supported hook names; the default hook registry is built as a dict comprehension over that list.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert 'response' in default_hooks()
>     assert default_hooks()['response'] == []
>     assert 'request' in default_hooks()
>     assert default_hooks()['request'] == []
>     assert len(default_hooks()) == 2
>     assert 'response' in HOOKS and 'request' in HOOKS and len(HOOKS) == 2
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

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
