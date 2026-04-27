# v1 #69 edit_skip_leading_empty_chunks_extend_whitespace

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='extend-skip-predicate', scope_kind='single-file', answer_shape='value-equality', unique_trait='extend-empty-skip-to-whitespace-only-bytes-keep-pass-through'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `_skip_leading_empty_chunks` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_transports/wsgi.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `httpx` checkout, the small private helper inside the WSGI transport module currently drops only strictly-empty (`b''`) leading byte chunks from a stream of body fragments. Real-world WSGI applications occasionally yield whitespace-only chunks (`b' '`, `b'\t'`, `b'\n  \t'`) as bookkeeping output before the first real fragment, and downstream consumers expect those to be skipped just like empty chunks are. Extend the leading-skip predicate so that:
> 
> - Leading whitespace-only `bytes`/`bytearray`/`str` chunks are also skipped. For example, `list(helper([b'  ', b'\t', b'foo', b'bar']))` returns `[b'foo', b'bar']`, and `list(helper([b'\n  \t', b'foo']))` returns `[b'foo']`.
> - Existing behaviour on truly-empty leading chunks is preserved exactly: `list(helper([b'', b'foo', b'bar']))` returns `[b'foo', b'bar']`. An empty input still returns `[]`.
> - The pass-through-after-first-non-empty contract is preserved: `list(helper([b'foo', b'  ', b'bar']))` returns `[b'foo', b'  ', b'bar']` (whitespace AFTER the first real chunk is forwarded unchanged); a single-element non-empty stream like `list(helper([b'foo']))` returns `[b'foo']`.
> - Non-`bytes`/`bytearray`/`str` chunks must continue to be evaluated by their truthiness only (the helper is generic over chunk types), so the whitespace check applies only when the chunk is a `bytes`, `bytearray`, or `str`.
> 
> The minimal change extends the existing single `if chunk:` predicate to also reject whitespace-only `bytes`/`bytearray`/`str` chunks. Do NOT modify the `itertools.chain([chunk], body)` pass-through or the `return []` fallback. The helper lives among the WSGI integration glue under `httpx`; locate it by searching for `WSGI` or `itertools.chain` in the codebase.

## Ground truth (reference edit)

`httpx/_transports/wsgi.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def _skip_leading_empty_chunks(body: typing.Iterable[_T]) -> typing.Iterable[_T]:
    body = iter(body)
    for chunk in body:
        if chunk:
            return itertools.chain([chunk], body)
    return []
```

```python
# newString
def _skip_leading_empty_chunks(body: typing.Iterable[_T]) -> typing.Iterable[_T]:
    body = iter(body)
    for chunk in body:
        if chunk and (
            not isinstance(chunk, (bytes, bytearray, str)) or chunk.strip()
        ):
            return itertools.chain([chunk], body)
    return []
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `list(_skip_leading_empty_chunks([b'', b'foo', b'bar'])) == [b'foo', b'bar']` |
| 2 | regression | over-edit | `list(_skip_leading_empty_chunks([])) == []` |
| 3 | regression | over-edit | `list(_skip_leading_empty_chunks([b'foo', b'  ', b'bar'])) == [b'foo', b'  ', b'bar']` |
| 4 | regression | over-edit | `list(_skip_leading_empty_chunks([b'foo'])) == [b'foo']` |
| 5 | new_behavior | no-change | `list(_skip_leading_empty_chunks([b'  ', b'\t', b'foo', b'bar'])) == [b'foo', b'bar']` |
| 6 | new_behavior | partial-edit | `list(_skip_leading_empty_chunks([b'\n  \t', b'foo'])) == [b'foo']` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def _skip_leading_empty_chunks` -> `httpx/_transports/wsgi.py`
- `WSGI` -> `httpx/__init__.py`, `httpx/_transports/__init__.py`, `httpx/_transports/wsgi.py`
- `itertools.chain` -> `httpx/_transports/wsgi.py`

- Union (D = 3): `httpx/__init__.py`, `httpx/_transports/__init__.py`, `httpx/_transports/wsgi.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> In this `httpx` checkout, locate the helper described below and patch it so that the behavior contract holds. The helper lives somewhere under `httpx/`; find it by searching the repo for the behavior described.
> 
> > The target is a small private helper inside `httpx`'s WSGI transport that drops leading empty byte chunks from an iterable of body fragments before they reach the response. It currently treats only the truly-empty chunk `b''` as 'leading skippable noise' -- whitespace-only chunks like `b' '` or `b'\t'` are forwarded as the first chunk, which prevents downstream consumers from inspecting the real first content fragment.
> 
> Behavior contract:
> 
> In this `httpx` checkout, the small private helper inside the WSGI transport module currently drops only strictly-empty (`b''`) leading byte chunks from a stream of body fragments. Real-world WSGI applications occasionally yield whitespace-only chunks (`b' '`, `b'\t'`, `b'\n  \t'`) as bookkeeping output before the first real fragment, and downstream consumers expect those to be skipped just like empty chunks are. Extend the leading-skip predicate so that:
> 
> - Leading whitespace-only `bytes`/`bytearray`/`str` chunks are also skipped. For example, `list(helper([b'  ', b'\t', b'foo', b'bar']))` returns `[b'foo', b'bar']`, and `list(helper([b'\n  \t', b'foo']))` returns `[b'foo']`.
> - Existing behaviour on truly-empty leading chunks is preserved exactly: `list(helper([b'', b'foo', b'bar']))` returns `[b'foo', b'bar']`. An empty input still returns `[]`.
> - The pass-through-after-first-non-empty contract is preserved: `list(helper([b'foo', b'  ', b'bar']))` returns `[b'foo', b'  ', b'bar']` (whitespace AFTER the first real chunk is forwarded unchanged); a single-element non-empty stream like `list(helper([b'foo']))` returns `[b'foo']`.
> - Non-`bytes`/`bytearray`/`str` chunks must continue to be evaluated by their truthiness only (the helper is generic over chunk types), so the whitespace check applies only when the chunk is a `bytes`, `bytearray`, or `str`.
> 
> The minimal change extends the existing single `if chunk:` predicate to also reject whitespace-only `bytes`/`bytearray`/`str` chunks. Do NOT modify the `itertools.chain([chunk], body)` pass-through or the `return []` fallback. The helper lives among the WSGI integration glue under `httpx`; locate it by searching for `WSGI` or `itertools.chain` in the codebase.
> 
> Constraints:
> - Edit exactly ONE file inside `httpx/`. Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`httpx/_transports/wsgi.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `list(_skip_leading_empty_chunks([b'', b'foo', b'bar'])) == [b'foo', b'bar']` (kind: regression)
- **over-edit**: caught by `list(_skip_leading_empty_chunks([])) == []` (kind: regression)
- **over-edit**: caught by `list(_skip_leading_empty_chunks([b'foo', b'  ', b'bar'])) == [b'foo', b'  ', b'bar']` (kind: regression)
- **over-edit**: caught by `list(_skip_leading_empty_chunks([b'foo'])) == [b'foo']` (kind: regression)
- **no-change**: caught by `list(_skip_leading_empty_chunks([b'  ', b'\t', b'foo', b'bar'])) == [b'foo', b'bar']` (kind: new_behavior)
- **partial-edit**: caught by `list(_skip_leading_empty_chunks([b'\n  \t', b'foo'])) == [b'foo']` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `[b'  ', b'\t', b'foo']` still yields `[b'  ', b'\t', b'foo']` instead of `[b'foo']` (`no-change`).
- Adds the whitespace check but applies it to ALL chunks (not just leading), so `list(helper([b'foo', b'  ', b'bar']))` becomes `[b'foo', b'bar']` instead of `[b'foo', b'  ', b'bar']` (`over-edit`).
- Strips whitespace too aggressively (e.g. checks `chunk.isspace()` on bytes which is a method that exists but interprets the encoding loosely), passing for `b'\xc2\xa0'` (non-breaking space in UTF-8) when it shouldn't (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
