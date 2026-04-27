# v1 #67 edit_get_auth_from_url_partial_recovery

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='partial-auth-recovery', scope_kind='single-file', answer_shape='value-equality', unique_trait='extract-username-when-password-missing-keep-empty-tuple-fallback'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `get_auth_from_url` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `get_auth_from_url` (declared at module scope inside `requests`) so that a URL with only a username is decoded partially rather than collapsed to the empty tuple:
> 
> - Calling `get_auth_from_url('http://user@host.example/path')` now returns `('user', '')`. Percent-decoding still applies to the present field, so `get_auth_from_url('http://us%40er@host.example/path')` returns `('us@er', '')` (the `%40` becomes `@`).
> - Existing behaviour on every other input is preserved exactly: `get_auth_from_url('http://user:pass@host.example/path')` returns `('user', 'pass')`; `get_auth_from_url('')` returns `('', '')`; `get_auth_from_url('http://host.example/path')` (no auth at all) returns `('', '')`; and percent-decoding on both fields still works -- `get_auth_from_url('https://us%40er:p%23ss@host.example/path')` returns `('us@er', 'p#ss')`.
> 
> The minimal change is to compute `username` and `password` separately, defaulting each to the empty string when the corresponding component on the parsed URL is `None` rather than passing `None` to `unquote` and relying on the broad `except` to swallow the `TypeError`. Keep the surrounding `try`/`except (AttributeError, TypeError)` block in place as the safety net for genuinely malformed URLs.

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth
```

```python
# newString
def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        username = unquote(parsed.username) if parsed.username is not None else ""
        password = unquote(parsed.password) if parsed.password is not None else ""
        auth = (username, password)
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `get_auth_from_url('http://user:pass@host.example/path') == ('user', 'pass')` |
| 2 | regression | over-edit | `get_auth_from_url('') == ('', '')` |
| 3 | regression | over-edit | `get_auth_from_url('http://host.example/path') == ('', '')` |
| 4 | regression | over-edit | `get_auth_from_url('https://us%40er:p%23ss@host.example/path') == ('us@er', 'p#ss')` |
| 5 | new_behavior | no-change | `get_auth_from_url('http://user@host.example/path') == ('user', '')` |
| 6 | new_behavior | partial-edit | `get_auth_from_url('http://us%40er@host.example/path') == ('us@er', '')` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def get_auth_from_url` -> `src/requests/utils.py`
- `get_auth_from_url` -> `src/requests/adapters.py`, `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`
- `auth_from_url` -> `src/requests/adapters.py`, `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`

- Union (D = 4): `src/requests/adapters.py`, `src/requests/models.py`, `src/requests/sessions.py`, `src/requests/utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> Modify the function `get_auth_from_url` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the `get_auth_from_url` helper declared at module scope inside `requests`. It parses a URL via `urlparse` and returns a `(username, password)` tuple, percent-decoded. Today, when only the username is present (e.g. `http://user@host.example/path`), the existing code calls `unquote(parsed.password)` -- where `parsed.password` is `None` -- which raises `TypeError`; the broad `except (AttributeError, TypeError)` catches it and the function returns `('', '')`, throwing away the username it could have recovered.
> 
> Behavior contract:
> 
> Modify the function `get_auth_from_url` (declared at module scope inside `requests`) so that a URL with only a username is decoded partially rather than collapsed to the empty tuple:
> 
> - Calling `get_auth_from_url('http://user@host.example/path')` now returns `('user', '')`. Percent-decoding still applies to the present field, so `get_auth_from_url('http://us%40er@host.example/path')` returns `('us@er', '')` (the `%40` becomes `@`).
> - Existing behaviour on every other input is preserved exactly: `get_auth_from_url('http://user:pass@host.example/path')` returns `('user', 'pass')`; `get_auth_from_url('')` returns `('', '')`; `get_auth_from_url('http://host.example/path')` (no auth at all) returns `('', '')`; and percent-decoding on both fields still works -- `get_auth_from_url('https://us%40er:p%23ss@host.example/path')` returns `('us@er', 'p#ss')`.
> 
> The minimal change is to compute `username` and `password` separately, defaulting each to the empty string when the corresponding component on the parsed URL is `None` rather than passing `None` to `unquote` and relying on the broad `except` to swallow the `TypeError`. Keep the surrounding `try`/`except (AttributeError, TypeError)` block in place as the safety net for genuinely malformed URLs.
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `get_auth_from_url('http://user:pass@host.example/path') == ('user', 'pass')` (kind: regression)
- **over-edit**: caught by `get_auth_from_url('') == ('', '')` (kind: regression)
- **over-edit**: caught by `get_auth_from_url('http://host.example/path') == ('', '')` (kind: regression)
- **over-edit**: caught by `get_auth_from_url('https://us%40er:p%23ss@host.example/path') == ('us@er', 'p#ss')` (kind: regression)
- **no-change**: caught by `get_auth_from_url('http://user@host.example/path') == ('user', '')` (kind: new_behavior)
- **partial-edit**: caught by `get_auth_from_url('http://us%40er@host.example/path') == ('us@er', '')` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `get_auth_from_url('http://user@host.example/path')` still returns `('', '')` and the username is silently lost (`no-change`).
- Recovers the username when the password is missing but also stops percent-decoding (e.g. uses `parsed.username` directly instead of `unquote(parsed.username)`), so `'us%40er'` no longer round-trips to `'us@er'` (`partial-edit`).
- Removes the broad `except (AttributeError, TypeError)` safety net entirely, so a genuinely malformed URL now propagates an exception instead of returning `('', '')` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
