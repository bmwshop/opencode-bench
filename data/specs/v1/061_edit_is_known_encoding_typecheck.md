# v1 #61 edit_is_known_encoding_typecheck

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='add-guard', scope_kind='single-file', answer_shape='raises-with-substring', unique_trait='raise-on-non-str-encoding-keep-codec-lookup'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `_is_known_encoding` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_models.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `_is_known_encoding` (declared at module scope inside `httpx`) so that it gracefully rejects non-string inputs:
> 
> - Calling `_is_known_encoding(x)` where `x` is not a `str` instance now raises `ValueError` whose message contains the substring `encoding`. For example, `_is_known_encoding(123)` raises `ValueError`, and `_is_known_encoding(None)` raises `ValueError`.
> - Existing behaviour on string inputs is preserved exactly: `_is_known_encoding('utf-8')` returns `True`, `_is_known_encoding('utf-16')` returns `True`, and `_is_known_encoding('not-a-real-codec')` returns `False`.
> 
> The minimal change is a single guard at the top of the function body that runs before `codecs.lookup` is called; do NOT change the existing `codecs.lookup` / `LookupError` logic.

## Ground truth (reference edit)

`httpx/_models.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def _is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True
```

```python
# newString
def _is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    if not isinstance(encoding, str):
        raise ValueError(f"_is_known_encoding: encoding must be a str, got {type(encoding).__name__}")
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True
```


## Hidden truth table (graders only) (N = 5)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `_is_known_encoding('utf-8') is True` |
| 2 | regression | over-edit | `_is_known_encoding('utf-16') is True` |
| 3 | regression | over-edit | `_is_known_encoding('not-a-real-codec') is False` |
| 4 | new_behavior | no-change | `raised is not None and 'encoding' in str(raised)` _(with setup)_ |
| 5 | new_behavior | partial-edit | `raised is not None and 'encoding' in str(raised)` _(with setup)_ |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def _is_known_encoding` -> `httpx/_models.py`
- `default_encoding` -> `httpx/_client.py`, `httpx/_models.py`
- `codecs.lookup` -> `httpx/_models.py`

- Union (D = 2): `httpx/_client.py`, `httpx/_models.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> Modify the function `_is_known_encoding` inside the `httpx` package so that the behavior contract below holds:
> 
> > The target is the small private helper `_is_known_encoding` declared at module scope inside `httpx`. It currently accepts any value, calls `codecs.lookup` on it, and returns `True`/`False` based on whether a `LookupError` is raised; with non-string input it instead crashes with `TypeError` from inside `codecs.lookup`.
> 
> Behavior contract:
> 
> Modify the function `_is_known_encoding` (declared at module scope inside `httpx`) so that it gracefully rejects non-string inputs:
> 
> - Calling `_is_known_encoding(x)` where `x` is not a `str` instance now raises `ValueError` whose message contains the substring `encoding`. For example, `_is_known_encoding(123)` raises `ValueError`, and `_is_known_encoding(None)` raises `ValueError`.
> - Existing behaviour on string inputs is preserved exactly: `_is_known_encoding('utf-8')` returns `True`, `_is_known_encoding('utf-16')` returns `True`, and `_is_known_encoding('not-a-real-codec')` returns `False`.
> 
> The minimal change is a single guard at the top of the function body that runs before `codecs.lookup` is called; do NOT change the existing `codecs.lookup` / `LookupError` logic.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_models.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `_is_known_encoding('utf-8') is True` (kind: regression)
- **over-edit**: caught by `_is_known_encoding('utf-16') is True` (kind: regression)
- **over-edit**: caught by `_is_known_encoding('not-a-real-codec') is False` (kind: regression)
- **no-change**: caught by `raised is not None and 'encoding' in str(raised)` (kind: new_behavior)
- **partial-edit**: caught by `raised is not None and 'encoding' in str(raised)` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so non-string input still crashes with TypeError from inside codecs.lookup (`no-change`).
- Catches the TypeError inside the existing try/except instead of raising ValueError up front, returning False on non-string input rather than raising (`partial-edit`).
- Raises ValueError but only for one specific non-string class (e.g. `int`), so other non-string inputs like `None` still crash (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
