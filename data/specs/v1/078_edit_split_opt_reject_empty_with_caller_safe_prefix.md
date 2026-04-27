# v1 #78 edit_split_opt_reject_empty_with_caller_safe_prefix

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **hard**
- leak_function_name: **false**
- structural_signature: `template='callee-strict-callsite-tolerant', scope_kind='multi-file', answer_shape='cross-file-pair', unique_trait='callee-rejects-empty-option-caller-returns-empty-prefix'`

## Repo

`click` - pallets/click, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/click/`.

## Criterion (mechanical)

- Target function (primary): `_split_opt` (plus in-file callees: _(none)_)
- Target file(s): `src/click/parser.py`, `src/click/formatting.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `click` checkout, satisfy a defensive contract spread across two related files inside `src/click/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level helper (in the click parser module whose top-of-file docstring begins `This module started out as largely a copy paste from the stdlib's optparse module`):
> 
> - Today, the helper returns `('', '')` when called on the empty string `''` -- a degenerate result that downstream code can mistake for a legitimate `('', name)` shape.
> - Tighten the helper so that an empty `opt` (the empty string `''`, or any other falsy value) raises `ValueError` with the message text `option splitter received empty input` (case-sensitive substring). The check must happen BEFORE the existing `first = opt[:1]` line.
> - All existing behaviour is preserved exactly for non-empty inputs: `'--foo'` still returns `('--', 'foo')`; `'-x'` still returns `('-', 'x')`; `'foo'` still returns `('', 'foo')` (alphanumeric first char keeps the empty prefix); `'-'` still returns `('', '-')`. Only the empty-string input changes behaviour (now raises).
> 
> Higher-level helper (in the click formatting module that already houses `measure_table`, `iter_rows`, and `wrap_text`, and that already imports the lower-level option splitter from the sibling parser module):
> 
> - Add a NEW top-level helper named `_split_opt_prefix_safe(opt)` that returns just the prefix component of a CLI option token without raising on bad input. It must:
>   - Return `''` (the empty string) when `opt` is `None`.
>   - Return `''` when `opt` is not a `str` (e.g. an integer, a list, etc.).
>   - Return `''` when `opt` is an empty string (so this case never reaches the lower-level helper, which would now raise).
>   - Otherwise delegate to the lower-level option splitter and return just the prefix component (the FIRST element of the returned tuple).
> - For example: `_split_opt_prefix_safe(None)` returns `''`; `_split_opt_prefix_safe('')` returns `''`; `_split_opt_prefix_safe('--foo')` returns `'--'`; `_split_opt_prefix_safe('-x')` returns `'-'`; `_split_opt_prefix_safe('foo')` returns `''` (bare alphanumeric); `_split_opt_prefix_safe(123)` returns `''` (non-string).
> 
> Locate the lower-level helper by searching for the docstring substring `started out as largely a copy paste`. Locate the sibling caller file by searching for the existing top-level `measure_table` helper.

## Ground truth (reference edit)

`src/click/parser.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def _split_opt(opt: str) -> tuple[str, str]:
    first = opt[:1]
    if first.isalnum():
        return "", opt
    if opt[1:2] == first:
        return opt[:2], opt[2:]
    return first, opt[1:]
```

```python
# newString
def _split_opt(opt: str) -> tuple[str, str]:
    if not opt:
        raise ValueError("option splitter received empty input")
    first = opt[:1]
    if first.isalnum():
        return "", opt
    if opt[1:2] == first:
        return opt[:2], opt[2:]
    return first, opt[1:]
```

`src/click/formatting.py` (oldString occurs exactly once in the baseline):

```python
# oldString
        yield row + ("",) * (col_count - len(row))


def wrap_text(
```

```python
# newString
        yield row + ("",) * (col_count - len(row))


def _split_opt_prefix_safe(opt):
    """Defensive wrapper that returns the option-prefix portion of ``opt``
    (e.g. ``'--'`` for ``'--foo'``, ``'-'`` for ``'-x'``, ``''`` for a
    bare alphanumeric token) without raising on empty/None input.

    Returns ``''`` (empty string) when ``opt`` is None, not a string, or
    an empty string. Otherwise delegates to the lower-level option
    splitter and returns just the prefix component (the first element
    of the returned tuple).
    """
    if opt is None:
        return ""
    if not isinstance(opt, str):
        return ""
    if not opt:
        return ""
    return _split_opt(opt)[0]


def wrap_text(
```


## Hidden truth table (graders only) (N = 11)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `_split_opt('--foo') == ('--', 'foo')` |
| 2 | regression | over-edit | `_split_opt('-x') == ('-', 'x')` |
| 3 | regression | over-edit | `_split_opt('foo') == ('', 'foo')` |
| 4 | regression | over-edit | `_split_opt('-') == ('-', '')` |
| 5 | new_behavior | no-change | `_raised is not None and 'empty input' in _raised` _(with setup)_ |
| 6 | new_behavior | no-change | `_split_opt_prefix_safe(None) == ''` |
| 7 | new_behavior | no-change | `_split_opt_prefix_safe('') == ''` |
| 8 | new_behavior | partial-edit | `_split_opt_prefix_safe('--foo') == '--'` |
| 9 | new_behavior | partial-edit | `_split_opt_prefix_safe('-x') == '-'` |
| 10 | new_behavior | partial-edit | `_split_opt_prefix_safe('foo') == ''` |
| 11 | new_behavior | partial-edit | `_split_opt_prefix_safe(123) == ''` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/click/` hits across these probes. The manifest pins D in `[2, 4]`:

- `started out as largely a copy paste` -> `src/click/parser.py`
- `measure_table` -> `src/click/formatting.py`

- Union (D = 2): `src/click/formatting.py`, `src/click/parser.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> In this `click` checkout, satisfy the cross-file behavior contract below. The change requires consistent edits in TWO related files inside `src/click/`. Find the relevant files by searching the repo for the behavior described.
> 
> > The target spans two related files inside `src/click/`. The lower-level helper is a tiny utility in the click parser module (whose top-of-file docstring mentions that it `started out as largely a copy paste` of the stdlib's optparse) that splits a CLI option token like `'--foo'` into its prefix part (`'--'`) and its name part (`'foo'`); for bare alphanumeric tokens it returns an empty prefix. The higher-level caller is the click formatting module that already houses `measure_table`, `iter_rows`, and `wrap_text`; it currently consumes the prefix returned by the lower-level helper directly without guarding against empty or non-string inputs.
> 
> Behavior contract:
> 
> In this `click` checkout, satisfy a defensive contract spread across two related files inside `src/click/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level helper (in the click parser module whose top-of-file docstring begins `This module started out as largely a copy paste from the stdlib's optparse module`):
> 
> - Today, the helper returns `('', '')` when called on the empty string `''` -- a degenerate result that downstream code can mistake for a legitimate `('', name)` shape.
> - Tighten the helper so that an empty `opt` (the empty string `''`, or any other falsy value) raises `ValueError` with the message text `option splitter received empty input` (case-sensitive substring). The check must happen BEFORE the existing `first = opt[:1]` line.
> - All existing behaviour is preserved exactly for non-empty inputs: `'--foo'` still returns `('--', 'foo')`; `'-x'` still returns `('-', 'x')`; `'foo'` still returns `('', 'foo')` (alphanumeric first char keeps the empty prefix); `'-'` still returns `('', '-')`. Only the empty-string input changes behaviour (now raises).
> 
> Higher-level helper (in the click formatting module that already houses `measure_table`, `iter_rows`, and `wrap_text`, and that already imports the lower-level option splitter from the sibling parser module):
> 
> - Add a NEW top-level helper named `_split_opt_prefix_safe(opt)` that returns just the prefix component of a CLI option token without raising on bad input. It must:
>   - Return `''` (the empty string) when `opt` is `None`.
>   - Return `''` when `opt` is not a `str` (e.g. an integer, a list, etc.).
>   - Return `''` when `opt` is an empty string (so this case never reaches the lower-level helper, which would now raise).
>   - Otherwise delegate to the lower-level option splitter and return just the prefix component (the FIRST element of the returned tuple).
> - For example: `_split_opt_prefix_safe(None)` returns `''`; `_split_opt_prefix_safe('')` returns `''`; `_split_opt_prefix_safe('--foo')` returns `'--'`; `_split_opt_prefix_safe('-x')` returns `'-'`; `_split_opt_prefix_safe('foo')` returns `''` (bare alphanumeric); `_split_opt_prefix_safe(123)` returns `''` (non-string).
> 
> Locate the lower-level helper by searching for the docstring substring `started out as largely a copy paste`. Locate the sibling caller file by searching for the existing top-level `measure_table` helper.
> 
> Constraints:
> - Edit exactly TWO files inside `src/click/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Use exactly the exception class(es) named in the contract (`ValueError`); other classes will not satisfy the hidden grader.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/click/parser.py`, `src/click/formatting.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `_split_opt('--foo') == ('--', 'foo')` (kind: regression)
- **over-edit**: caught by `_split_opt('-x') == ('-', 'x')` (kind: regression)
- **over-edit**: caught by `_split_opt('foo') == ('', 'foo')` (kind: regression)
- **over-edit**: caught by `_split_opt('-') == ('-', '')` (kind: regression)
- **no-change**: caught by `_raised is not None and 'empty input' in _raised` (kind: new_behavior)
- **no-change**: caught by `_split_opt_prefix_safe(None) == ''` (kind: new_behavior)
- **no-change**: caught by `_split_opt_prefix_safe('') == ''` (kind: new_behavior)
- **partial-edit**: caught by `_split_opt_prefix_safe('--foo') == '--'` (kind: new_behavior)
- **partial-edit**: caught by `_split_opt_prefix_safe('-x') == '-'` (kind: new_behavior)
- **partial-edit**: caught by `_split_opt_prefix_safe('foo') == ''` (kind: new_behavior)
- **partial-edit**: caught by `_split_opt_prefix_safe(123) == ''` (kind: new_behavior)

## Fail modes

- Edits only the lower-level helper to raise on empty input but never adds the new sibling helper, so the new-behavior asserts on `_split_opt_prefix_safe` fail (`partial-edit`).
- Adds the sibling helper but doesn't tighten the lower-level helper, so calling the lower-level helper directly with `''` still returns `('', '')` instead of raising (`partial-edit`).
- Adds the sibling helper but returns the entire `(prefix, rest)` tuple instead of just the prefix component, breaking the assertion that `_split_opt_prefix_safe('--foo') == '--'` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
