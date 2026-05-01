# v1 #15 synthesize_primitive_value_demo

## Category

code_authoring (artifact-creation family: write a runnable demo script
from scratch given a target API spec).

## Contract

completion

## Surface

tools

## Repo

`httpx` — encode/httpx, pinned via `data/v1_repos.json`. The agent
operates in a per-run copy of the submodule checkout at
`projects/v1/httpx/`.

## Capability

The artifact-creation atomic skill (per Ma et al. arXiv:2604.05013):
read a target helper deep inside a real package's internals module,
derive its non-obvious special-case behavior (the helper does NOT use
`str()` for booleans / `None` -- it has its own JSON-style mappings),
and produce a runnable demo script that exercises the helper across a
mixed input set and prints output in a strict format. The discriminating
inputs (boolean `True` → `'true'`, boolean `False` → `'false'`, integer
`0` → `'0'`) catch a common "naive `str()` reimplementation" failure
mode in one needle each.

## Setup

The per-run fixture is a pinned copy of `encode/httpx`. The target
helper is a small primitive-value coercion function inside
`httpx/_utils.py` -- a private internals module. `demo_primitive.py`
does not pre-exist.

The target helper has the following input → output mapping at the pinned
commit:

| input             | output     |
|-------------------|------------|
| `True`            | `'true'`   |
| `False`           | `'false'`  |
| `None`            | `''`       |
| `42` (int)        | `'42'`     |
| `3.14` (float)    | `'3.14'`   |
| `'hello'` (str)   | `'hello'`  |
| `''` (empty str)  | `''`       |
| `0` (int)         | `'0'`      |

Crucially, `True` / `False` / `None` produce *lowercase JSON-style*
output, not `str(True)` / `str(False)` / `str(None)` (which would be
`'True'` / `'False'` / `'None'`). And integer `0` produces `'0'`, not
`'False'` (boolean falsy collapse) -- proving the model handled type,
not truthiness.

## De-leak status

Function name (`primitive_value_to_str`) is deliberately omitted from
the prompt. The model must locate it by reading `httpx/_utils.py`
(named in the prompt because it is part of the import contract). The
behavior contract ("Python's `True` / `False` / `None` are NOT coerced
via `str()`, they have their own special-case mappings") is described
in prose to discriminate the helper from any near-by helpers without
naming it.

## Prompt

> In this `httpx` repo, the small internals module `httpx/_utils.py`
> defines a primitive-value coercion helper that turns single primitive
> values (booleans, `None`, ints, floats, strings) into their JSON-style
> display string representation -- notably, Python's `True` / `False`
> / `None` are NOT coerced via `str()`, they have their own
> special-case mappings. Read the helper to derive its exact behavior,
> then create a script `demo_primitive.py` at the repo root that:
>
> - Imports the helper from `httpx._utils` (`from httpx._utils import
>   ...` resolves through the per-run stub on PYTHONPATH).
> - For each input in the list `[True, False, None, 42, 3.14, 'hello',
>   '', 0]`, prints exactly one line in the format
>   `input=<v> output=<r>` where `<v>` is `repr(input)` (so the line
>   for the empty string is unambiguous) and `<r>` is the helper's
>   return value rendered as-is (no quoting -- print the helper's
>   exact return string).
> - Does NOT modify `httpx/_utils.py`.
>
> Runnable as `python demo_primitive.py`.

## Pass criteria (2 checks)

1. `exec_function` `script=demo_primitive.py`,
   `source=httpx/_utils.py`, `functions=[primitive_value_to_str]`,
   `expect_stdout_contains=["input=True output=true",
   "input=False output=false", "input=42 output=42",
   "input='hello' output=hello", "input=0 output=0"]`,
   `timeout=10s`. Passes iff the stub builds, the subprocess exits
   0, and all five needles appear in stdout. Five chosen because:
   - `input=True output=true` and `input=False output=false` rule out
     a naive `str()` implementation (which would produce capitalized
     `True` / `False`).
   - `input=42 output=42` and `input='hello' output=hello` confirm
     non-special inputs pass through `str()`.
   - `input=0 output=0` rules out a "treat falsy as boolean" bug
     (which would produce `output=false` for `0`).
2. `call_schema_valid` — every tool call in the trace matches
   opencode's canonical JSON schemas.

### Why the nested package import works

`exec_function` mirrors the source's relative path inside its tempdir
stub: for `source=httpx/_utils.py` it writes
`tempdir/httpx/_utils.py` plus an empty `tempdir/httpx/__init__.py`,
then prepends `tempdir` to `PYTHONPATH`. The student's
`from httpx._utils import primitive_value_to_str` resolves to the stub
without ever touching the real `httpx` package's heavy imports
(`httpcore`, `anyio`, etc.).

## Shortest path

**2 tool calls**: `read httpx/_utils.py` (to locate the helper and
confirm its branching for booleans, `None`, etc.) → `write
demo_primitive.py`.

## Fail modes

- **Script not created** — `exec_function` reports `script not found:
  demo_primitive.py`.
- **Wrong import path / import of a non-exported name** — subprocess
  fails with `ImportError`.
- **Naive `str()` reimplementation** (model writes `print(f'input={v!r}
  output={str(v) if v is not None else ""}')` without calling the
  helper) — `input=True output=true` needle fails (it would be
  `output=True` capitalized).
- **Wrong format** (e.g. quotes around output, or different prefix) —
  needles miss.
- **Skipped inputs** (model only emitted lines for some of the 8
  inputs) — surviving needles will catch any of the five
  discriminative cases that wasn't emitted.
- **Modified `httpx/_utils.py`** (model edited the helper) — stub
  reflects the edit; output may no longer match the pinned needles.
- **Runaway script** — 10s timeout fires.
- **Fixture damage** — harness-level reason (source `SyntaxError` /
  target function not found).
- **Malformed tool args** — `call_schema_valid` fails.

## Known ceilings

- A model that hardcodes the five needle strings as `print` literals
  — without actually calling the helper — passes. Acceptable: the
  model still had to read the helper to know the special-case
  behavior for `True`, `False`, `None` (the only way to predict
  lowercase output is to see the source).

## Note on methodology

This sample is part of v1's three-sample artifact-creation family
(#13, #14, #15). It exercises the same skill as #13 / #14 but on a
different repo (`httpx` rather than `autoresearch`) and with a more
discriminative needle set targeting a non-obvious special-case
behavior. The nested-package import path tests the
`exec_function` evaluator's ability to mirror source paths inside the
stub tempdir.
