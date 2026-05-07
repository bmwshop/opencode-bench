# v1 #60 edit_address_in_network_invalid_with_caller

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Prompt

> In this `requests` checkout, satisfy the cross-file behavior contract below. The change requires consistent edits in TWO related files inside `src/requests/`. Find the relevant files by searching the repo for the behavior described.
> 
> > The target spans two related files: a CIDR-membership test in the `requests` utilities module, and a defensive wrapper the agent must add to the HTTP-adapter module so that proxy logic can call the membership test on potentially malformed inputs.
> 
> Behavior contract:
> 
> In this `requests` checkout, satisfy a defensive contract spread across two related files inside `src/requests/`. The change requires consistent edits in BOTH files; a single-file edit will not satisfy the hidden grader.
> 
> Lower-level helper (in the `requests` utilities module, alongside other small IP-address helpers):
> 
> - The helper today tests whether an IPv4 address belongs to a CIDR subnet; for the pair `('192.168.1.1', '192.168.1.0/24')` it returns `True`, and for `('192.168.2.1', '192.168.1.0/24')` it returns `False`. Currently it crashes with `OSError` or `ValueError` whenever the IP or CIDR string is malformed.
> - All existing behaviour on well-formed inputs must be preserved exactly: `('192.168.1.1', '192.168.1.0/24')` returns `True`, `('192.168.2.1', '192.168.1.0/24')` returns `False`, and `('10.0.0.5', '10.0.0.0/8')` returns `True`.
> - When the IP is not a parseable IPv4 string (e.g. `'not-an-ip'`), the helper must now return `False` (no exception escapes).
> - When the CIDR is not a parseable CIDR string (e.g. `'not-a-cidr'` with no `/`, or `'192.168.1.0/not-a-mask'` with a non-integer mask), the helper must now return `False` (no exception escapes).
> 
> Higher-level helper (in the sibling HTTP-adapter module that already imports several helpers from the utilities module via `from .utils import (...)`):
> 
> - Add a NEW top-level helper named `_proxy_target_in_network(target_ip, cidr)` that prefilters obviously bad arguments before delegating to the lower-level helper:
>   - If `target_ip` is `None` or an empty string, return `False`.
>   - If `cidr` is `None` or an empty string, return `False`.
>   - Otherwise delegate to the lower-level helper, returning whatever it returns.
> - For example: `_proxy_target_in_network(None, '192.168.1.0/24')` returns `False`; `_proxy_target_in_network('192.168.1.1', '192.168.1.0/24')` returns `True`.
> 
> Locate the lower-level helper by searching for the docstring phrase `IP belongs to a network subnet`; locate the sibling adapter file by searching for `HTTPAdapter` or for the existing module-level `DEFAULT_POOLBLOCK` constant.
> 
> Constraints:
> - Edit exactly TWO files inside `src/requests/` (one impl + one caller that depends on it). Do not add new files.
> - Preserve every behavior not explicitly changed by the contract above; regression-style behavior must continue to hold.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` (`src/requests/utils.py`, `src/requests/adapters.py`) - patched code must satisfy the full behavioral assertion set for this sample.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Fail modes

- Edits only the lower-level helper (returns `False` on bad inputs) but never adds the sibling adapter wrapper, so the `_proxy_target_in_network` asserts fail (`partial-edit`).
- Adds the sibling wrapper but doesn't touch the lower-level helper, so malformed CIDR/IP strings still propagate `OSError` / `ValueError` from the implementation (`partial-edit`).
- Catches `Exception` broadly inside the lower-level helper, masking genuine bugs in the bit-arithmetic body (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch matches a particular diff shape - any semantically equivalent patch that satisfies the graded behavior is accepted.
