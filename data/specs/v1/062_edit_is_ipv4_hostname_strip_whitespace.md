# v1 #62 edit_is_ipv4_hostname_strip_whitespace

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **easy**
- leak_function_name: **true**
- structural_signature: `template='relax-validator', scope_kind='single-file', answer_shape='value-equality', unique_trait='accept-leading-trailing-whitespace-keep-cidr-strip'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `is_ipv4_hostname` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> Modify the function `is_ipv4_hostname` (declared at module scope inside `httpx`) so that surrounding whitespace on the input is tolerated:
> 
> - Calling `is_ipv4_hostname(s)` with leading or trailing whitespace (spaces, tabs, newlines) on an otherwise valid IPv4 hostname now returns `True`. For example, `is_ipv4_hostname('   1.2.3.4   ')` returns `True`, and `is_ipv4_hostname('\t1.2.3.4/32\n')` returns `True`.
> - Existing behaviour on whitespace-free inputs is preserved exactly: `is_ipv4_hostname('1.2.3.4')` returns `True`; the trailing CIDR mask is still stripped before the address parse, so `is_ipv4_hostname('1.2.3.4/32')` returns `True`; `is_ipv4_hostname('not-an-ip')` returns `False`; `is_ipv4_hostname('')` returns `False`.
> 
> The minimal change normalises whitespace on the input before the existing CIDR-stripping `.split('/')` call. Do NOT change the existing `IPv4Address` parse logic or the `except Exception: return False` fallback.

## Ground truth (reference edit)

`httpx/_utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def is_ipv4_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv4Address(hostname.split("/")[0])
    except Exception:
        return False
    return True
```

```python
# newString
def is_ipv4_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv4Address(hostname.strip().split("/")[0])
    except Exception:
        return False
    return True
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `is_ipv4_hostname('1.2.3.4') is True` |
| 2 | regression | over-edit | `is_ipv4_hostname('1.2.3.4/32') is True` |
| 3 | regression | over-edit | `is_ipv4_hostname('not-an-ip') is False` |
| 4 | regression | over-edit | `is_ipv4_hostname('') is False` |
| 5 | new_behavior | no-change | `is_ipv4_hostname('   1.2.3.4   ') is True` |
| 6 | new_behavior | partial-edit | `is_ipv4_hostname('\t1.2.3.4/32\n') is True` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def is_ipv4_hostname` -> `httpx/_utils.py`
- `ipaddress.IPv4Address` -> `httpx/_urlparse.py`, `httpx/_utils.py`
- `is_ipv6_hostname` -> `httpx/_utils.py`

- Union (D = 2): `httpx/_urlparse.py`, `httpx/_utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **true**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

## Prompt

> Modify the function `is_ipv4_hostname` inside the `httpx` package so that the behavior contract below holds:
> 
> > The target is the small `is_ipv4_hostname` predicate declared at module scope inside `httpx`. It currently calls `hostname.split('/')[0]` directly; the `IPv4Address` parser then rejects any input with stray leading/trailing whitespace, so an otherwise-valid hostname like `'  1.2.3.4  '` returns `False`.
> 
> Behavior contract:
> 
> Modify the function `is_ipv4_hostname` (declared at module scope inside `httpx`) so that surrounding whitespace on the input is tolerated:
> 
> - Calling `is_ipv4_hostname(s)` with leading or trailing whitespace (spaces, tabs, newlines) on an otherwise valid IPv4 hostname now returns `True`. For example, `is_ipv4_hostname('   1.2.3.4   ')` returns `True`, and `is_ipv4_hostname('\t1.2.3.4/32\n')` returns `True`.
> - Existing behaviour on whitespace-free inputs is preserved exactly: `is_ipv4_hostname('1.2.3.4')` returns `True`; the trailing CIDR mask is still stripped before the address parse, so `is_ipv4_hostname('1.2.3.4/32')` returns `True`; `is_ipv4_hostname('not-an-ip')` returns `False`; `is_ipv4_hostname('')` returns `False`.
> 
> The minimal change normalises whitespace on the input before the existing CIDR-stripping `.split('/')` call. Do NOT change the existing `IPv4Address` parse logic or the `except Exception: return False` fallback.
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

- **no-change**: caught by `is_ipv4_hostname('1.2.3.4') is True` (kind: regression)
- **over-edit**: caught by `is_ipv4_hostname('1.2.3.4/32') is True` (kind: regression)
- **over-edit**: caught by `is_ipv4_hostname('not-an-ip') is False` (kind: regression)
- **over-edit**: caught by `is_ipv4_hostname('') is False` (kind: regression)
- **no-change**: caught by `is_ipv4_hostname('   1.2.3.4   ') is True` (kind: new_behavior)
- **partial-edit**: caught by `is_ipv4_hostname('\t1.2.3.4/32\n') is True` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so `is_ipv4_hostname('  1.2.3.4  ')` still returns `False` because the `IPv4Address` parser rejects whitespace (`no-change`).
- Strips whitespace from the input but only for the leading side (e.g. `lstrip()` instead of `strip()`), so trailing-whitespace inputs still return `False` (`partial-edit`).
- Strips whitespace globally (e.g. removes all internal spaces too), accidentally accepting malformed inputs like `'1.2 . 3 . 4'` (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
