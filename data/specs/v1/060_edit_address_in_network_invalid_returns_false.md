# v1 #60 edit_address_in_network_invalid_returns_false

## Category

code_editing

## Contract

completion

## Surface

tools

## Repo

`requests` - psf/requests, pinned via `data/v1_repos.json`. The agent operates in a per-run copy of the submodule checkout at `projects/v1/requests/`.

## Criterion (mechanical)

- Target function: `address_in_network` (plus in-file callees: `dotted_netmask`)
- Target file: `src/requests/utils.py` (pinned at `79f4df84cf77`; deliberately NOT named in the prompt)
- Match semantics: every assertion in the truth table below must pass when the target function and its listed callees / constants / imports are AST-extracted from the patched file and evaluated in a fresh namespace by `evaluators.content.exec_assert`.

## Ground truth (reference edit)

Applied once against `src/requests/utils.py` at pin `79f4df84cf77`; `oldString` occurs exactly once in the baseline file.

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

## Truth table (N = 6)

Each assert is tagged with its kind (regression vs new_behavior) and the misstep it catches.

| # | kind | misstep | assertion |
|---|------|---------|-----------|
| 1 | regression | no-change | `address_in_network('192.168.1.1', '192.168.1.0/24') is True` |
| 2 | regression | over-edit | `address_in_network('192.168.2.1', '192.168.1.0/24') is False` |
| 3 | regression | over-edit | `address_in_network('10.0.0.5', '10.0.0.0/8') is True` |
| 4 | new_behavior | no-change | `address_in_network('not-an-ip', '192.168.1.0/24') is False` |
| 5 | new_behavior | partial-edit | `address_in_network('192.168.1.1', 'not-a-cidr') is False` |
| 6 | new_behavior | partial-edit | `address_in_network('192.168.1.1', '192.168.1.0/not-a-mask') is False` |

## Discovery probes (D-gate)

The prompt deliberately does NOT name the file; the agent must discover it. D is the cardinality of the union of `rg -l <pattern> src/requests/` hits across these probes. The manifest pins D in `[2, 4]` (medium difficulty):

- `def address_in_network` -> `src/requests/utils.py`
- `subnet` -> `src/requests/utils.py`
- `network` -> `src/requests/models.py`, `src/requests/status_codes.py`, `src/requests/utils.py`

- Union (D = 3): `src/requests/models.py`, `src/requests/status_codes.py`, `src/requests/utils.py`

## Determinism contract

The prompt pins, with no room for judgment:

- The target function name (`address_in_network`) is named verbatim.
- Every literal value referenced by an assert appears in the prompt (via the truth table itself).
- Every exception class used in `try/except` setups is named verbatim.
- Every new-behavior input->output pair appears concretely as a Python assertion.
- The prompt contains no banned fuzz words (reasonable / appropriate / sensible / generally / usually / as needed / makes sense / if you think / suitable).
- The prompt does not name the file path.

## Prompt

> Modify the function `address_in_network` inside the `requests` package so that EVERY one of the following Python assertions passes simultaneously, as executed against the AST-extracted source of the patched function. The function delegates to the helper(s) `dotted_netmask` in the same file; you may edit that helper too if the asserts require it.
> 
> Context (no file path leaked; locate the target by searching the repo):
> > The target tests whether an IPv4 address belongs to a CIDR subnet. It lives in the `requests` utilities module alongside other small IP-address helpers, and delegates the mask conversion to `dotted_netmask`.
> 
> Assertions that must ALL pass (this is the oracle; treat it as a truth table):
> 
>     assert address_in_network('192.168.1.1', '192.168.1.0/24') is True
>     assert address_in_network('192.168.2.1', '192.168.1.0/24') is False
>     assert address_in_network('10.0.0.5', '10.0.0.0/8') is True
>     assert address_in_network('not-an-ip', '192.168.1.0/24') is False
>     assert address_in_network('192.168.1.1', 'not-a-cidr') is False
>     assert address_in_network('192.168.1.1', '192.168.1.0/not-a-mask') is False
> 
> Constraints:
> - Edit exactly ONE file inside `src/requests/`. Do not add new files.
> - Preserve every regression assert; do not delete existing behavior.
> - Use the exact exception class names that appear in the assertions above (e.g. `ValueError`, `TypeError`) -- other classes will not satisfy the asserts.
> - Keep the edit minimal and localized; do not refactor unrelated code.

## Pass criteria (2 checks)

1. `exec_assert` `src/requests/utils.py` - every entry in the truth table above evaluates True against the patched file (AST-extracted function bodies, pinned constants, pinned imports). One `exec_assert` invocation returns exactly one pass/fail over the whole list.
2. `call_schema_valid` - every tool call in the trace matches opencode's canonical JSON schemas.

## Shortest path

**3 tool calls** minimum: one `grep` / `bash` to locate the file, one `read` to anchor the edit, and one `edit` to apply the change. Any refactor that makes all asserts pass while leaving no other file modified scores a pass.

## Assert-to-misstep map

Each misstep tag documents which *wrong* edit the assert exists to catch:

- **no-change**: caught by `address_in_network('192.168.1.1', '192.168.1.0/24') is True` (kind: regression)
- **over-edit**: caught by `address_in_network('192.168.2.1', '192.168.1.0/24') is False` (kind: regression)
- **over-edit**: caught by `address_in_network('10.0.0.5', '10.0.0.0/8') is True` (kind: regression)
- **no-change**: caught by `address_in_network('not-an-ip', '192.168.1.0/24') is False` (kind: new_behavior)
- **partial-edit**: caught by `address_in_network('192.168.1.1', 'not-a-cidr') is False` (kind: new_behavior)
- **partial-edit**: caught by `address_in_network('192.168.1.1', '192.168.1.0/not-a-mask') is False` (kind: new_behavior)

## Fail modes

- Leaves the function unchanged, so invalid IP/CIDR inputs propagate `OSError` / `ValueError` (`no-change`).
- Catches `Exception` broadly, masking genuine bugs elsewhere in the body (`over-edit`).
- Handles bad IPs but not bad CIDR strings (e.g. catches only `OSError` but not `ValueError` from `int(bits)`) (`partial-edit`).

## Intentionally *not* checked

- Free-form explanation in the response text - only the patched file is scored.
- Which tools the agent uses to explore - `grep` / `read` / `glob` / `bash` are all acceptable as long as exactly one file inside `src/requests/` changes and every tool call validates.
- Whether the agent's patch uses the same `oldString`/`newString` as the reference edit - any semantically equivalent patch that satisfies the truth table is accepted.

## Note on methodology

This sample defines the ground truth **mechanically** as a list of Python assertions over AST-extracted function bodies against a pinned SHA. It extends the criterion-anchored pattern established for v1 #21-#30 (see `scripts/regen_localization.py`). The prompt ships the asserts verbatim: an agent can self-verify its edit by evaluating the truth table in a REPL. Any dispute over correctness is settled mechanically by re-running `exec_assert`; there is no LLM judge.
