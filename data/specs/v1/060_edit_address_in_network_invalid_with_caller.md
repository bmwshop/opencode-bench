# v1 #60 edit_address_in_network_invalid_with_caller

## Category

code_editing

## Contract

completion

## Surface

tools

## Difficulty / structural signature

- difficulty: **hard**
- leak_function_name: **false**
- structural_signature: `template='cross-file-contract', scope_kind='multi-file', answer_shape='cross-file-pair', unique_trait='impl-validates-caller-prefilters'`

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function (primary): `address_in_network` (plus in-file callees: `dotted_netmask`)
- Target file(s): `src/requests/utils.py`, `src/requests/adapters.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the hidden truth table below must pass when the target function(s) and their listed callees / constants / imports are AST-extracted from the patched file(s) and evaluated in a single shared namespace by `evaluators.content.exec_assert`.

## Behavior prose (in prompt)

This is the natural-language behavior contract the agent sees -- the leaked truth table is gone.

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

## Ground truth (reference edit)

`src/requests/utils.py` (oldString occurs exactly once in the baseline):

```python
# oldString
def address_in_network(ip, net):
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24

    :rtype: bool
    """
    ipaddr = struct.unpack("=L", socket.inet_aton(ip))[0]
    netaddr, bits = net.split("/")
    netmask = struct.unpack("=L", socket.inet_aton(dotted_netmask(int(bits))))[0]
    network = struct.unpack("=L", socket.inet_aton(netaddr))[0] & netmask
    return (ipaddr & netmask) == (network & netmask)
```

```python
# newString
def address_in_network(ip, net):
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24

    :rtype: bool
    """
    try:
        ipaddr = struct.unpack("=L", socket.inet_aton(ip))[0]
        netaddr, bits = net.split("/")
        netmask = struct.unpack("=L", socket.inet_aton(dotted_netmask(int(bits))))[0]
        network = struct.unpack("=L", socket.inet_aton(netaddr))[0] & netmask
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return (ipaddr & netmask) == (network & netmask)
```

`src/requests/adapters.py` (oldString occurs exactly once in the baseline):

```python
# oldString
DEFAULT_POOLBLOCK = False
DEFAULT_POOLSIZE = 10
DEFAULT_RETRIES = 0
DEFAULT_POOL_TIMEOUT = None


def _urllib3_request_context(
```

```python
# newString
DEFAULT_POOLBLOCK = False
DEFAULT_POOLSIZE = 10
DEFAULT_RETRIES = 0
DEFAULT_POOL_TIMEOUT = None


def _proxy_target_in_network(target_ip, cidr):
    """Defensive wrapper for CIDR membership testing in proxy logic.

    Returns ``False`` when either ``target_ip`` or ``cidr`` is ``None``
    or an empty string, otherwise delegates to ``address_in_network``
    (which is itself defensive against malformed IP / CIDR strings).
    """
    if target_ip is None or target_ip == "":
        return False
    if cidr is None or cidr == "":
        return False
    return address_in_network(target_ip, cidr)


def _urllib3_request_context(
```


## Hidden truth table (graders only) (N = 10)

This block is shown for review purposes; **it is NOT in the prompt**. Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `address_in_network('192.168.1.1', '192.168.1.0/24') is True` |
| 2 | regression | over-edit | `address_in_network('192.168.2.1', '192.168.1.0/24') is False` |
| 3 | regression | over-edit | `address_in_network('10.0.0.5', '10.0.0.0/8') is True` |
| 4 | new_behavior | no-change | `address_in_network('not-an-ip', '192.168.1.0/24') is False` |
| 5 | new_behavior | partial-edit | `address_in_network('192.168.1.1', 'not-a-cidr') is False` |
| 6 | new_behavior | partial-edit | `address_in_network('192.168.1.1', '192.168.1.0/not-a-mask') is False` |
| 7 | new_behavior | no-change | `_proxy_target_in_network(None, '192.168.1.0/24') is False` |
| 8 | new_behavior | partial-edit | `_proxy_target_in_network('', '192.168.1.0/24') is False` |
| 9 | new_behavior | partial-edit | `_proxy_target_in_network('192.168.1.1', None) is False` |
| 10 | new_behavior | partial-edit | `_proxy_target_in_network('192.168.1.1', '192.168.1.0/24') is True` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]`:

- `def address_in_network` -> `src/requests/utils.py`
- `HTTPAdapter` -> `src/requests/adapters.py`, `src/requests/sessions.py`
- `DEFAULT_POOLBLOCK` -> `src/requests/adapters.py`

- Union (D = 3): `src/requests/adapters.py`, `src/requests/sessions.py`, `src/requests/utils.py`

## De-leak contract

The prompt pins, with no room for judgment:

- Function name leakage: **false**.
- Every exception class referenced by a hidden assert is named verbatim in the prose (and `'X' in str(...)` substrings, where used).
- Every literal in `prompt_required_literals` appears verbatim.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name any target file path.
- The prompt contains zero `assert ` substrings.

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

1. `exec_assert` (`src/requests/utils.py`, `src/requests/adapters.py`) - every entry in the hidden truth table above evaluates True against the patched file(s) (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**4 tool calls** minimum: one `grep` / `bash` to locate the file, a second `grep`/`read` to locate the cross-file caller, one `read` to anchor the edit, and one `edit` per target file to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `address_in_network('192.168.1.1', '192.168.1.0/24') is True` (kind: regression)
- **over-edit**: caught by `address_in_network('192.168.2.1', '192.168.1.0/24') is False` (kind: regression)
- **over-edit**: caught by `address_in_network('10.0.0.5', '10.0.0.0/8') is True` (kind: regression)
- **no-change**: caught by `address_in_network('not-an-ip', '192.168.1.0/24') is False` (kind: new_behavior)
- **partial-edit**: caught by `address_in_network('192.168.1.1', 'not-a-cidr') is False` (kind: new_behavior)
- **partial-edit**: caught by `address_in_network('192.168.1.1', '192.168.1.0/not-a-mask') is False` (kind: new_behavior)
- **no-change**: caught by `_proxy_target_in_network(None, '192.168.1.0/24') is False` (kind: new_behavior)
- **partial-edit**: caught by `_proxy_target_in_network('', '192.168.1.0/24') is False` (kind: new_behavior)
- **partial-edit**: caught by `_proxy_target_in_network('192.168.1.1', None) is False` (kind: new_behavior)
- **partial-edit**: caught by `_proxy_target_in_network('192.168.1.1', '192.168.1.0/24') is True` (kind: new_behavior)

## Fail modes

- Edits only the lower-level helper (returns `False` on bad inputs) but never adds the sibling adapter wrapper, so the `_proxy_target_in_network` asserts fail (`partial-edit`).
- Adds the sibling wrapper but doesn't touch the lower-level helper, so malformed CIDR/IP strings still propagate `OSError` / `ValueError` from the implementation (`partial-edit`).
- Catches `Exception` broadly inside the lower-level helper, masking genuine bugs in the bit-arithmetic body (`over-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file(s) are scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as the changed file set matches `targets` and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the hidden truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (localization) and is now de-leaked: the prompt no longer ships the asserts verbatim, only the natural-language contract derived from them. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
