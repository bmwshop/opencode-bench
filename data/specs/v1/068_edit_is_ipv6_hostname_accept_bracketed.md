# v1 #68 edit_is_ipv6_hostname_accept_bracketed

## Category

code_editing

## Repo

`httpx` - encode/httpx, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/httpx/`.

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

1. `exec_assert` (`httpx/_utils.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Leaves the helper unchanged, so `'[::1]'` still raises inside the parser and the broad except returns `False` (`no-change`).
- Strips brackets unconditionally on every character, so `'[2001:db8]::[1]'`-shaped inputs lose internal brackets and accidentally accept malformed addresses (`over-edit`).
- Strips only the leading `[` (e.g. `lstrip('[')` without `rstrip(']')`), so trailing-bracket cases still fail (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
