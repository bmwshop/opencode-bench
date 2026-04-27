# v1 #63 edit_primitive_value_to_str_decode_bytes

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='tighten-guard', scope_kind='single-file', answer_shape='value-equality', unique_trait='decode-bytes-as-utf8-keep-other-primitives'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `primitive_value_to_str` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `primitive_value_to_str` (declared at module scope inside `httpx`) so that it decodes `bytes` and `bytearray` values into UTF-8 text rather than falling through to `str(value)`:
> 
> - Calling `primitive_value_to_str(b'hello')` now returns `'hello'`. Calling `primitive_value_to_str(b'')` returns `''`. The decoding uses UTF-8.
> - Existing behaviour on the other primitives is preserved exactly: `primitive_value_to_str(True)` returns `'true'`, `primitive_value_to_str(False)` returns `'false'`, `primitive_value_to_str(None)` returns `''`, `primitive_value_to_str(123)` returns `'123'`, and `primitive_value_to_str('hello')` returns `'hello'`.
> 
> The minimal change is a single new branch inserted before the trailing `return str(value)` fallback. Do NOT modify the existing True/False/None branches.

## Ground truth (reference edit)

`httpx/_utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def primitive_value_to_str(value: PrimitiveData) -> str:
    """
    Coerce a primitive data type into a string value.

    Note that we prefer JSON-style 'true'/'false' for boolean values here.
    """
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return ""
    return str(value)
```

```python
# newString
def primitive_value_to_str(value: PrimitiveData) -> str:
    """
    Coerce a primitive data type into a string value.

    Note that we prefer JSON-style 'true'/'false' for boolean values here.
    """
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return ""
    elif isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8")
    return str(value)
```


## Hidden truth table (graders only) (N = 7)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `primitive_value_to_str(True) == 'true'` |
| 2 | regression | over-edit | `primitive_value_to_str(False) == 'false'` |
| 3 | regression | over-edit | `primitive_value_to_str(None) == ''` |
| 4 | regression | over-edit | `primitive_value_to_str(123) == '123'` |
| 5 | regression | over-edit | `primitive_value_to_str('hello') == 'hello'` |
| 6 | new_behavior | no-change | `primitive_value_to_str(b'hello') == 'hello'` |
| 7 | new_behavior | partial-edit | `primitive_value_to_str(b'') == ''` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def primitive_value_to_str` -> `httpx/_utils.py`
- `PrimitiveData` -> `httpx/_types.py`, `httpx/_utils.py`
- `JSON-style` -> `httpx/_utils.py`

- Union (D = 2): `httpx/_types.py`, `httpx/_utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> Modify the function `primitive_value_to_str` inside the `httpx` package so that the behavior contract below holds:
> 
> > The target is the small `primitive_value_to_str` coercion helper declared at module scope inside `httpx`. It currently maps `True` -> `'true'`, `False` -> `'false'`, `None` -> `''`, and falls back to `str(value)` for everything else; that fallback turns `bytes` values into ugly `"b'hello'"`-style repr strings instead of decoded text.
> 
> Behavior contract:
> 
> Modify the function `primitive_value_to_str` (declared at module scope inside `httpx`) so that it decodes `bytes` and `bytearray` values into UTF-8 text rather than falling through to `str(value)`:
> 
> - Calling `primitive_value_to_str(b'hello')` now returns `'hello'`. Calling `primitive_value_to_str(b'')` returns `''`. The decoding uses UTF-8.
> - Existing behaviour on the other primitives is preserved exactly: `primitive_value_to_str(True)` returns `'true'`, `primitive_value_to_str(False)` returns `'false'`, `primitive_value_to_str(None)` returns `''`, `primitive_value_to_str(123)` returns `'123'`, and `primitive_value_to_str('hello')` returns `'hello'`.
> 
> The minimal change is a single new branch inserted before the trailing `return str(value)` fallback. Do NOT modify the existing True/False/None branches.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_utils.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `primitive_value_to_str(True) == 'true'` (kind: regression)
- **over-edit**: caught by `primitive_value_to_str(False) == 'false'` (kind: regression)
- **over-edit**: caught by `primitive_value_to_str(None) == ''` (kind: regression)
- **over-edit**: caught by `primitive_value_to_str(123) == '123'` (kind: regression)
- **over-edit**: caught by `primitive_value_to_str('hello') == 'hello'` (kind: regression)
- **no-change**: caught by `primitive_value_to_str(b'hello') == 'hello'` (kind: new_behavior)
- **partial-edit**: caught by `primitive_value_to_str(b'') == ''` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `primitive_value_to_str(b'hello')` still returns the ugly Python-repr form `"b'hello'"` (`no-change`).
- Decodes the bytes but uses the wrong codec (e.g. `latin-1`) so non-ASCII bytes round-trip incorrectly even though the simple `b'hello'` case happens to work (`partial-edit`).
- Catches bytes via the `str(value)` branch by special-casing inside an existing branch (e.g. moves the check inside the `is None` branch) and accidentally also returns `''` for non-empty bytes (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
