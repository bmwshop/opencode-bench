# Building structured-output code-editing samples

This playbook explains how to add a new v1-style code-editing sample to
`opencode-bench`. It mirrors the workflow used for localization samples in
[building_localization_samples.md](building_localization_samples.md), with one
crucial difference: the ground truth here is a list of Python assertions
that the *patched* function must satisfy, not a sorted set of qualnames.

The process is validated against the pinned `requests` repo (samples
IDs 51-60).

## 1. Overview

A v1 editing sample asks the model to make a minimal patch to an
existing function (or, on the hard tier, a small cross-file set of
functions) so that a hidden truth table of behavioural assertions
passes. The agent never sees the asserts directly: the prompt encodes
the contract in prose and concrete I/O examples. Grading is mechanical
and runs in a single subprocess via
[evaluators/content/exec_assert.py](../evaluators/content/exec_assert.py).

There are three difficulty tiers:

* **easy** — single-file, additive change, function name leaked in
  prompt for discoverability.
* **medium** — single-file, function name *hidden*; the agent must
  discover the helper from behaviour terms in the prose.
* **hard** — multi-file, function name hidden; the patch must touch at
  least 2 files (typically impl + caller in a sibling module).

Ground truth is validated by a 7-layer protocol that runs every cheap
mutation up front so a passing audit means: the reference edit really
satisfies the asserts, the baseline really doesn't, regression asserts
really capture pre-existing behaviour, declared mutants really fail,
and (on hard tier) each cross-file half really fails alone.

## 2. Prerequisites

* Python 3.11+.
* `rg` (ripgrep) on `PATH` — the audit uses it for discovery probes.
* Target repo pinned as a git submodule at `projects/v1/<repo>/` and
  registered in [data/v1_repos.json](../data/v1_repos.json).
* Existing manifests at
  [data/v1_editing_criteria.json](../data/v1_editing_criteria.json)
  (the single source of truth) and
  [data/samples_v1.jsonl](../data/samples_v1.jsonl) (regenerated).

## 3. Anatomy of an editing sample

Every entry in `data/v1_editing_criteria.json` carries:

| field | purpose |
|-------|---------|
| `id`, `name`              | sample id (51..) and short slug |
| `file` *or* `targets[]`   | single-file path, or a list of `{path, functions, constants, imports, reference_edit}` for multi-file hard-tier samples |
| `functions`               | top-level functions to AST-extract (target + same-file callees) |
| `constants` / `imports`   | extra namespace hydration for asserts |
| `reference_edit`          | `{oldString, newString}` demonstrating one valid fix; `oldString` MUST occur exactly once in the baseline |
| `asserts[]`               | classified `{expr, kind, misstep, [setup]}` truth-table entries; every assert must pass on the patched file(s) |
| `mutants[]`               | optional misstep-tagged mutation patches that MUST fail the asserts (validates the truth table is tight) |
| `discovery_probes[]`      | rg patterns derived from prompt terms; their union must hit 2-4 files (medium D-gate) |
| `prompt_capability`       | 1-2 sentence behaviour summary for the prompt header |
| `behavior_prose`          | the full natural-language behaviour contract (replaces the leaked truth table) |
| `prompt_fail_modes`       | 3 concrete ways the edit can go wrong; renders into the spec |
| `difficulty`              | `easy` \| `medium` \| `hard` |
| `structural_signature`    | `{template, scope_kind, answer_shape, unique_trait}` for diversity tracking |
| `leak_function_name`      | bool. `true` = function name allowed verbatim in prompt; `false` (default for medium/hard) = must NOT appear |

## 4. End-to-end workflow

### 4.1 Propose a candidate

```bash
python3 scripts/propose_editing_candidates.py --top 15
python3 scripts/propose_editing_candidates.py --tier hard --multi-file
```

The proposer walks `src/requests/`, ranks functions by an editability
heuristic (LOC sweet-spot, branch count, has-docstring, in-repo caller
fan-out), and emits a ranked list along with a predicted difficulty,
template hint (`add-guard` / `tighten-guard` / `relax-validator` /
`extend-comprehension` / `swap-generator`), and (in `--multi-file`
mode) suggested cross-file caller pairings.

Pick a candidate whose `template_hint` and tier you can flesh out, and
draft a stub.

### 4.2 Author the manifest entry

Compose a JSON entry with the schema above. Critical authoring rules:

* `oldString` must be **unique** in the baseline file (and unique in
  each target on multi-file). If it isn't, expand it with surrounding
  context until it is.
* The asserts must include **at least one regression** assert (proves
  the patch doesn't break existing behaviour) and **at least one
  new_behavior** assert. The audit also requires 3+ distinct
  non-`none` `misstep` classes — this guarantees the assert list is
  trying to catch multiple kinds of wrong patches.
* Provide concrete I/O examples and exception-class names *verbatim*
  in `behavior_prose`; the audit's literal-coverage gate matches by
  string. No fuzz words (`reasonable`, `appropriate`, `sensible`,
  `generally`, `usually`, `as needed`, `where it makes sense`,
  `if you think`, `suitable`).
* Declare 2+ `mutants[]` entries: at minimum one `no-change` mutant
  (just the baseline) and one `over-edit`/`partial-edit` mutant. Each
  one feeds the L3 ground-truth gate.
* Set `leak_function_name`: `true` for easy samples, `false` for
  medium and hard.
* Set `structural_signature`: every sample's tuple
  `(template, scope_kind, answer_shape, unique_trait)` should be
  distinct from existing entries; if the first three collide, vary
  `unique_trait` (e.g. `"raises-on-zero-and-negative"` vs
  `"raises-on-zero-only"`).

### 4.3 Score the candidate

```bash
python3 scripts/score_editing_candidate.py /tmp/my_candidate.json
```

The scorer runs five gates:

| gate | what it proves |
|------|----------------|
| **L1** | reference patch applies cleanly + every assert passes |
| **L2** | the un-patched baseline FAILS the full assert list (otherwise `new_behavior` asserts test nothing) |
| **L2b** | the regression-only sub-list PASSES on the baseline (otherwise regression asserts encode post-edit state) |
| **L3** | every declared mutant fails ≥ 1 assert (proves the truth table is tight) |
| **L6** | hard-tier multi-file: applying just one half of the patch fails ≥ 1 assert (proves the cross-file edit is genuinely required) |

Iterate on the entry until all five gates pass. Then promote into the
manifest.

### 4.4 Register and regenerate

Add the entry to `data/v1_editing_criteria.json`, then regenerate
specs and JSONL rows:

```bash
python3 scripts/regen_editing.py
```

`regen_editing.py` runs Layer-0 authoring gates (anchor uniqueness,
AST presence, assert classification, D-gate, determinism) and rewrites
`data/specs/v1/0NN_<name>.md` plus the matching row in
`data/samples_v1.jsonl`. The spec markdown carries a hidden
`## Hidden truth table (graders only)` block so reviewers can see
exactly what gets graded.

### 4.5 Audit

```bash
python3 scripts/audit_editing.py
```

This runs both passes:

* **Pass 1 (in-process)** — re-runs every regen gate plus the L1/L2/L2b
  ground-truth checks against the pinned source, validates row ↔
  manifest consistency, materializes a syntax-error variant to verify
  exec_assert reports the failure correctly, and enforces the de-leak
  gates (zero `assert ` substrings in prompt, no fuzz words, literal
  coverage of exception classes / required substrings / I/O examples,
  `leak_function_name` flag honoured, hard-tier samples touch ≥ 2
  files).
* **Pass 2 (end-to-end)** — synthesizes a minimal opencode trace whose
  `edit` tool call uses canonical schema fields, materializes the
  per-sample workspace under a fake `runs/` tree, runs `eval.py`
  against it, and verifies both checks pass; then synthesizes a
  malformed-args trace and verifies `call_schema_valid` fails.

If the audit passes, the sample is ready to ship.

## 5. Difficulty heuristic

Tag a sample by these signals:

* **easy** — function name leaked, single-file, edit is additive
  (e.g. add a guard clause), behaviour can be described with 1-2 I/O
  pairs, ≤ 1 branch in the original function.
* **medium** — function name hidden; single-file; the agent must
  *discover* the helper from prose like "the small pure-Python helper
  that lazily yields fixed-size chunks"; edit may broaden a guard or
  swap an internal data shape; expect 2-3 branches.
* **hard** — function name hidden; multi-file; the patch needs
  consistent edits in ≥ 2 files (impl + caller). The proposer's
  `--multi-file` mode surfaces real caller pairings.

## 6. Structural signature matrix

To keep the panel diverse, **no two samples may share the same
`(template, scope_kind, answer_shape)` triple**. The original rule
allowed collisions on three of four axes if the free-form
`unique_trait` differed; the panel pilot showed this was too lax
(samples #51 and #55 satisfied the old rule but Pearson-correlated at
`r = 1.0`, indicating they loaded on the same model capability). The
strengthened rule is enforced by `regen_editing.py`'s
`triple-uniqueness` authoring gate.

Vocabulary used so far:

* `template` — `add-guard` / `tighten-guard` / `relax-validator` /
  `extend-comprehension` / `swap-generator` / `cross-file-contract`.
* `scope_kind` — `single-file` / `multi-file`.
* `answer_shape` — `value-equality` / `raises-with-substring` /
  `idempotent` / `mutates-arg` / `cross-file-pair`.
* `unique_trait` — free-form short tag describing what makes this
  particular sample distinct (e.g. `"raises-on-zero-and-negative"`,
  `"none-still-yields-whole"`, `"caller-rewires-impl-arg"`). Now
  purely descriptive — does not contribute to the uniqueness gate.

The 6 templates × 2 scope_kinds × 5 answer_shapes vocabulary admits
60 distinct triples, comfortably above the planned 30-sample target.
If you exhaust the matrix in a single repo, expand to a second repo
(see Section 8) rather than relaxing the rule.

## 7. Common gotchas

* **Anchor not unique.** Expand `oldString` with surrounding context.
* **Regression-only fails on baseline (L2b).** A "regression" assert
  unintentionally encodes post-edit behaviour. Re-classify it as
  `new_behavior` or weaken it to a property both versions satisfy.
* **Mutant unexpectedly passes (L3).** The asserts are too loose —
  add an assert that distinguishes the mutant from the reference edit.
* **Multi-file half passes (L6).** The cross-file edit isn't actually
  required. Either pick a different file pairing or strengthen the
  asserts to cover the inter-file contract.
* **Discovery D outside [2, 4].** Tighten or broaden discovery probes
  until the rg union hits exactly 2-4 files. Too low = function name
  effectively leaked through a unique substring; too high = prose is
  too vague to be a contract.

## 8. Porting to a new repo

The editing toolchain is multi-repo by design. Adding a new pinned
repo (e.g. `httpx`) takes three small steps; no script edits are
required.

### 8.1 Register the repo

1. Pick a stable tag SHA from upstream and add the submodule:

   ```bash
   git submodule add https://github.com/<owner>/<repo> projects/v1/<repo>
   cd projects/v1/<repo> && git checkout <sha> && cd -
   ```

2. Append a new entry to [data/v1_repos.json](../data/v1_repos.json):

   ```json
   "<repo>": {
     "url": "https://github.com/<owner>/<repo>",
     "pin": "<sha>",
     "submodule_path": "projects/v1/<repo>",
     "default_scope": "<src-subdir>/",
     "description": "<one line>"
   }
   ```

   `default_scope` is the rg discovery-probe scope path *relative to
   the submodule root* (e.g. `src/requests/` for `requests`,
   `httpx/` for `httpx`, `""` for repos whose source lives at the
   submodule root). Empty string scans the whole repo.

### 8.2 Author samples for the new repo

Every editing-sample tool now reads `repo` from the manifest entry
itself; defaulting to `requests` for backward compat with #51-60. To
author a sample in the new repo, just include `"repo": "<slug>"` in
the manifest entry. The proposer accepts `--repo <slug>` (default
`requests`); the scorer reads `repo` from the candidate JSON; regen
and audit thread the slug through automatically.

### 8.3 Verify multi-repo cleanliness

Run the proposer against the new repo to size up the candidate
inventory:

```bash
python3 scripts/propose_editing_candidates.py --repo <slug> --top 30
python3 scripts/propose_editing_candidates.py --repo <slug> --tier hard --multi-file --top 15
```

Then write candidates, score them with `score_editing_candidate.py`,
register them in the manifest, and run regen + audit. Every existing
sample must remain green.

### 8.4 Backward-compat invariant

Re-running `regen_editing.py` and `audit_editing.py` against the
existing #51-60 manifest (no edits) must produce byte-identical
spec markdown and JSONL rows. This invariant is what lets us refactor
the multi-repo scaffolding without disturbing existing samples.
