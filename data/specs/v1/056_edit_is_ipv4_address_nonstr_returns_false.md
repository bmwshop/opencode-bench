# v1 #56 edit_is_ipv4_address_nonstr_returns_false

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='early-return-type-check', scope_kind='single-file', answer_shape='value-equality', unique_trait='non-string-input-returns-false'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `is_ipv4_address` (plus in-file callees: _(none)_)
- Target file(s): `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `is_ipv4_address` (declared at module scope inside the `requests` utilities module) so that it returns `False` (rather than raising `TypeError`) for any non-`str` input, while preserving its existing behaviour on string inputs:
> 
> - `is_ipv4_address(None)` now returns `False`.
> - `is_ipv4_address(123)` (any non-string integer) returns `False`.
> - `is_ipv4_address(b'192.168.1.1')` (bytes value) returns `False`.
> - All existing behaviour on string inputs is preserved exactly: `'192.168.1.1'` returns `True`, `'10.0.0.0'` returns `True`, `'not-an-ip'` returns `False`, and `'256.1.1.1'` returns `False`.
> 
> The minimal change is a single early-return guard at the top of the function body that checks `isinstance(string_ip, str)`. Do NOT broaden the guard to use `try`/`except Exception` (that masks genuine bugs).

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True
```

```python
# newString
def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    if not isinstance(string_ip, str):
        return False
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True
```


## Hidden truth table (graders only) (N = 7)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `is_ipv4_address('192.168.1.1') is True` |
| 2 | regression | over-edit | `is_ipv4_address('10.0.0.0') is True` |
| 3 | regression | over-edit | `is_ipv4_address('not-an-ip') is False` |
| 4 | regression | over-edit | `is_ipv4_address('256.1.1.1') is False` |
| 5 | new_behavior | no-change | `is_ipv4_address(None) is False` |
| 6 | new_behavior | partial-edit | `is_ipv4_address(123) is False` |
| 7 | new_behavior | partial-edit | `is_ipv4_address(b'192.168.1.1') is False` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def is_ipv4_address` -> `src/requests/utils.py`
- `is_ipv4_address` -> `src/requests/utils.py`
- `should_bypass_proxies` -> `src/requests/sessions.py`, `src/requests/utils.py`

- Union (D = 2): `src/requests/sessions.py`, `src/requests/utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> Modify the function `is_ipv4_address` inside the `requests` package so that the behavior contract below holds:
> 
> > The target is the predicate `is_ipv4_address` that tests whether a value is a valid textual IPv4 address. It lives in the `requests` utilities module alongside other small IP-address helpers.
> 
> Behavior contract:
> 
> Modify the function `is_ipv4_address` (declared at module scope inside the `requests` utilities module) so that it returns `False` (rather than raising `TypeError`) for any non-`str` input, while preserving its existing behaviour on string inputs:
> 
> - `is_ipv4_address(None)` now returns `False`.
> - `is_ipv4_address(123)` (any non-string integer) returns `False`.
> - `is_ipv4_address(b'192.168.1.1')` (bytes value) returns `False`.
> - All existing behaviour on string inputs is preserved exactly: `'192.168.1.1'` returns `True`, `'10.0.0.0'` returns `True`, `'not-an-ip'` returns `False`, and `'256.1.1.1'` returns `False`.
> 
> The minimal change is a single early-return guard at the top of the function body that checks `isinstance(string_ip, str)`. Do NOT broaden the guard to use `try`/`except Exception` (that masks genuine bugs).
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

- **no-change**: caught by `is_ipv4_address('192.168.1.1') is True` (kind: regression)
- **over-edit**: caught by `is_ipv4_address('10.0.0.0') is True` (kind: regression)
- **over-edit**: caught by `is_ipv4_address('not-an-ip') is False` (kind: regression)
- **over-edit**: caught by `is_ipv4_address('256.1.1.1') is False` (kind: regression)
- **no-change**: caught by `is_ipv4_address(None) is False` (kind: new_behavior)
- **partial-edit**: caught by `is_ipv4_address(123) is False` (kind: new_behavior)
- **partial-edit**: caught by `is_ipv4_address(b'192.168.1.1') is False` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so passing `None`/`int`/`bytes` crashes with `TypeError` instead of returning False (`no-change`).
- Catches all exceptions (`except Exception`) to mask the bug, which also silences genuine bugs in the body (`over-edit`).
- Accepts `bytes` as valid (because `socket.inet_aton` does accept bytes on some platforms) instead of rejecting everything that's not `str` (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
