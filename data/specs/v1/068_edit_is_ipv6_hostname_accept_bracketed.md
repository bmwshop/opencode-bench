# v1 #68 edit_is_ipv6_hostname_accept_bracketed

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **medium**
- leak_function_name: **false**
- structural_signature: `template='accept-bracketed-form', scope_kind='single-file', answer_shape='value-equality', unique_trait='strip-rfc3986-brackets-keep-cidr-strip'`

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

## Criterion (mechanical)

- Target function (primary): `is_ipv6_hostname` (plus in-file callees: _(none)_)
- Target file(s): `httpx/_utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

> In this `httpx` checkout, the small private predicate that decides whether a string is a valid IPv6 hostname currently rejects bracketed RFC-3986 forms even though those are exactly what URL parsers hand you when extracting the host component of `http://[::1]:8080/path`. Tighten the helper so that:
> 
> - A bracketed IPv6 hostname now parses as IPv6: `'[::1]'` returns `True`, and the bracketed-with-CIDR form `'[2001:db8::1]/64'` also returns `True`.
> - Existing behaviour on bare IPv6 inputs is preserved exactly: `'::1'` returns `True`; `'2001:db8::1'` returns `True`; the CIDR-stripping behaviour still runs, so `'::1/64'` returns `True`; and a non-IPv6 string like `'not-an-ip'` still returns `False`.
> 
> The minimal change strips a single leading `[` and a single trailing `]` from the input (when it is a `str`) before the existing CIDR-stripping `.split('/')` call. Do NOT modify the existing `IPv6Address` parse logic or the `except Exception: return False` fallback. The helper lives among the other small networking helpers in the `httpx` utilities module; locate it by searching for `ipaddress.IPv6Address` or for the sibling IPv4 predicate in the same module.

## Ground truth (reference edit)

`httpx/_utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def is_ipv6_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv6Address(hostname.split("/")[0])
    except Exception:
        return False
    return True
```

```python
# newString
def is_ipv6_hostname(hostname: str) -> bool:
    try:
        host_part = hostname.split("/")[0]
        if isinstance(host_part, str) and host_part.startswith("[") and host_part.endswith("]"):
            host_part = host_part[1:-1]
        ipaddress.IPv6Address(host_part)
    except Exception:
        return False
    return True
```


## Hidden truth table (graders only) (N = 6)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `is_ipv6_hostname('::1') is True` |
| 2 | regression | over-edit | `is_ipv6_hostname('2001:db8::1') is True` |
| 3 | regression | over-edit | `is_ipv6_hostname('::1/64') is True` |
| 4 | regression | over-edit | `is_ipv6_hostname('not-an-ip') is False` |
| 5 | new_behavior | no-change | `is_ipv6_hostname('[::1]') is True` |
| 6 | new_behavior | partial-edit | `is_ipv6_hostname('[2001:db8::1]/64') is True` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> httpx/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def is_ipv6_hostname` -> `httpx/_utils.py`
- `ipaddress.IPv6Address` -> `httpx/_urlparse.py`, `httpx/_utils.py`
- `IPv4Address` -> `httpx/_urlparse.py`, `httpx/_utils.py`

- Union (D = 2): `httpx/_urlparse.py`, `httpx/_utils.py`

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
> > The target is the small predicate that, in `httpx`'s URL-handling utilities, decides whether a hostname string parses as an IPv6 address. It currently passes the input directly (after a CIDR `/`-strip) to `ipaddress.IPv6Address`; bracketed RFC-3986 forms like `'[::1]'` -- the form a URL parser hands you when extracting `host` from `http://[::1]:8080/path` -- raise inside `IPv6Address` and the broad `except` branch then misclassifies them as non-IPv6.
> 
> Behavior contract:
> 
> In this `httpx` checkout, the small private predicate that decides whether a string is a valid IPv6 hostname currently rejects bracketed RFC-3986 forms even though those are exactly what URL parsers hand you when extracting the host component of `http://[::1]:8080/path`. Tighten the helper so that:
> 
> - A bracketed IPv6 hostname now parses as IPv6: `'[::1]'` returns `True`, and the bracketed-with-CIDR form `'[2001:db8::1]/64'` also returns `True`.
> - Existing behaviour on bare IPv6 inputs is preserved exactly: `'::1'` returns `True`; `'2001:db8::1'` returns `True`; the CIDR-stripping behaviour still runs, so `'::1/64'` returns `True`; and a non-IPv6 string like `'not-an-ip'` still returns `False`.
> 
> The minimal change strips a single leading `[` and a single trailing `]` from the input (when it is a `str`) before the existing CIDR-stripping `.split('/')` call. Do NOT modify the existing `IPv6Address` parse logic or the `except Exception: return False` fallback. The helper lives among the other small networking helpers in the `httpx` utilities module; locate it by searching for `ipaddress.IPv6Address` or for the sibling IPv4 predicate in the same module.
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

- **no-change**: caught by `is_ipv6_hostname('::1') is True` (kind: regression)
- **over-edit**: caught by `is_ipv6_hostname('2001:db8::1') is True` (kind: regression)
- **over-edit**: caught by `is_ipv6_hostname('::1/64') is True` (kind: regression)
- **over-edit**: caught by `is_ipv6_hostname('not-an-ip') is False` (kind: regression)
- **no-change**: caught by `is_ipv6_hostname('[::1]') is True` (kind: new_behavior)
- **partial-edit**: caught by `is_ipv6_hostname('[2001:db8::1]/64') is True` (kind: new_behavior)

## Fail modes

- Leaves the helper unchanged, so `'[::1]'` still raises inside the parser and the broad except returns `False` (`no-change`).
- Strips brackets unconditionally on every character, so `'[2001:db8]::[1]'`-shaped inputs lose internal brackets and accidentally accept malformed addresses (`over-edit`).
- Strips only the leading `[` (e.g. `lstrip('[')` without `rstrip(']')`), so trailing-bracket cases still fail (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
