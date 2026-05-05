# Building structured-output localization samples

This playbook explains how to add a new v3c-style localization sample to
`opencode-bench`. The process is designed so a fresh agent (e.g. Claude) can
propose, validate, and register a sample against any Python repository with
minimal hand-holding, using a small set of reusable helper scripts.

The process has been validated against the pinned `requests` repo (samples
IDs 21-50). It is intended to work against any other repo with a one-time
wiring step (see [Porting to a new repo](#porting-to-a-new-repo)).

## 1. Overview

A v3c localization sample asks the model to locate a small set of Python
functions in a pinned repo and write them to `location.txt` in the format
`file_path::QualifiedName`, sorted lexicographically. There are exactly two
templates:

* **T1 (anchor + direct callers)** — the answer is a *named anchor function*
  plus every function in scope that directly calls the anchor (sorted
  together).
* **T2 (callers of a set)** — the answer is every function in scope that
  directly calls any of a set of target names (the targets themselves are
  excluded).

Ground truth is derived *programmatically* from the repo AST by the oracle in
[data/scripts/localization_oracle.py](../localization_oracle.py) and
cross-checked against `rg`. A sample is considered valid only if the oracle
and `rg` agree and a five-layer verification passes (AST → rg → uniqueness
sanity → evaluator audit → pilot panel).

## 2. Prerequisites

* Python 3.11+ (the oracle uses `match`/`dataclass` features).
* `rg` (ripgrep) on `PATH` — the oracle cross-checks AST call sites against
  textual grep output.
* The target repo pinned as a git submodule at
  `projects/v1/<repo>/` and registered in
  [data/v1_repos.json](../../v1_repos.json) with its exact commit SHA.
* Repo name wired up in the oracle (see [Porting to a new repo](#porting-to-a-new-repo)
  for details).

## 3. The happy-path workflow (one sample)

1. **Propose candidates**

   ```bash
   python3 data/scripts/propose_localization_candidates.py \
     --repo requests \
     --scope src/requests \
     --tier hard \
     --validate
   ```

   The proposer walks the AST of every `.py` in the scope and emits two
   ranked lists (T1 and T2) with:
   * a predicted `structural_signature` stub;
   * a predicted `difficulty` tier (see [How to pick difficulty](#4-how-to-pick-difficulty));
   * a score reflecting cross-file spread, caller count, and trap presence;
   * a validation line (when `--validate` is passed) that re-runs the oracle
     against the top candidates and reports count-mismatches.

   Anchors / target sets already used by existing manifest entries are
   filtered out automatically; candidates whose predicted signature tuple
   collides with an existing entry are kept but penalized in the score.

2. **Pick one candidate** from the output. A good pick has:

   * `validated` in its notes;
   * 2 ≤ entries ≤ 12 (T1) or 3 ≤ entries ≤ 14 (T2);
   * a unique (template, scope_kind, anchor_kind|target_kind, entries, files)
     tuple against
     [data/scripts/json/v1_localization_criteria.json](../json/v1_localization_criteria.json);
   * a clear domain story (prefer functions whose name and role are
     self-evident — cookies, auth, redirects, proxies, hooks, etc.).

3. **Write a candidate stub** to `/tmp/cand.json` with the expected shape:

   ```jsonc
   // T1
   {
     "template": "T1",
     "scope": ["src/requests/cookies.py", "src/requests/sessions.py"],
     "anchor": {"file": "src/requests/cookies.py",
                "name": "merge_cookies",
                "module_level": true},
     "unique_trait_hint": "module_level_anchor_cross_file_fanin"
   }
   ```

   ```jsonc
   // T2
   {
     "template": "T2",
     "scope": "src/requests/",
     "targets": ["iter_content", "iter_lines", "raise_for_status", "close"],
     "target_kind": "response_consumer_methods",
     "unique_trait_hint": "callers_span_three_files"
   }
   ```

4. **Score** the candidate end-to-end:

   ```bash
   python3 data/scripts/score_localization_candidate.py --input /tmp/cand.json
   ```

   Must exit 0. The JSON payload includes the derived gold listing, the
   estimated difficulty, the per-call-site map, and a
   `signature_collisions` array. If `signature_collisions` is non-empty,
   the candidate has the same tuple as an existing sample — either pick a
   different candidate or change one of `scope`/`anchor`/`targets` to shift
   the structural signature.

5. **Append the manifest entry** to
   [data/scripts/json/v1_localization_criteria.json](../json/v1_localization_criteria.json)
   using the shape of the existing entries #21-30 as a template. Required
   keys:

   * `id`, `type: "structured_output"`, `difficulty`, `template`
   * `scope` (a list of files, or a directory string ending in `/`)
   * For T1: `anchor: {file, name, module_level}`
   * For T2: `targets: [name, ...]`
   * `structural_signature` (use the one the scorer reported, filling in
     `unique_trait` with a concise descriptor)
   * Prompt fields: `prompt_domain`, plus either
     `prompt_anchor_description` (T1) or `prompt_target_description` (T2) and
     `prompt_scope_description`
   * `output_path: "location.txt"`
   * `min_tool_calls`, `category: "code_localization"`

   See any of #21-30 for the expected field-by-field shape.

6. **Add a derive script** at `data/scripts/derive_0NN_ground_truth.py`. It is a
   4-line stub that calls the shared `run_derive_cli` helper:

   ```python
   from scripts.localization_oracle import run_derive_cli
   if __name__ == "__main__":
       run_derive_cli(sample_id=<NN>)
   ```

7. **Regenerate specs + jsonl**:

   ```bash
   python3 data/scripts/regen_structured_samples.py
   ```

8. **Audit**:

   ```bash
   python3 data/scripts/audit_localization_structured.py
   ```

   Must end with `RESULT: PASS`. Both pass-1 (structure + regex round-trip)
   and pass-2 (oracle rederivation) run.

9. **Pilot a single model run** before committing the sample to the full
   panel:

   ```bash
   python3 run.py --version v1 --id <NN> \
     --model nvidia-internal/azure/anthropic/claude-opus-4-6 \
     --timeout 1200
   ```

   Confirm the expected evaluator output (`file_regex_disk` pass,
   `call_schema_valid` pass).

## 4. How to pick difficulty

The proposer and scorer both use the same heuristic:

* **easy** — entries ≤ 3 **and** files ≤ 2 **and** no traps present.
* **hard** — entries ≥ 7 **or** files ≥ 4 **or** ≥ 1 trap present.
* **medium** — anything else.

"Traps" are:

1. `has_nested_def` — the anchor or any caller contains a nested `def`
   (closure / inner helper).
2. `name_collision` — a target (T2) shares its bare name with a non-target
   function elsewhere in scope, forcing the "exclusion by name" rule to
   actively remove entries.
3. `has_decorator` — the anchor has any decorator (`@property`, `@classmethod`,
   `@staticmethod`, or user-defined).
4. `has_async` — the anchor or any caller is an `async def`.

The human designer may override the auto-estimate. A common reason to
override *down* (hard → medium) is a very small answer with a nested def that
doesn't actually affect the gold entries; a common reason to override *up*
(medium → hard) is a T2 with an import-alias collision the heuristic doesn't
see.

When overriding, include a one-line justification in the manifest entry's
`notes` field (e.g. `"notes": "override: medium; nested_def is inside a
caller we exclude, so the trap is vacuous"`).

## 5. Structural-signature matrix

Every sample carries a `structural_signature` with the following dimensions.
The rule of thumb is that the *tuple* (template, scope_kind,
anchor_kind|target_kind, answer_entries, answer_files) must be unique across
the family; `unique_trait` is free-form and is the designer's escape hatch
when two candidates would otherwise share a tuple.

| Dimension          | Values used so far                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| `template`         | `T1`, `T2`                                                                                                   |
| `scope_kind`       | `single_file`, `two_files`, `three_files`, `four_files`, `any_file`                                          |
| `anchor_kind` (T1) | `module_level`, `instance_method`, `mixin_method`, `classmethod`, `staticmethod`, `property`, `async_method`, `nested_closure` |
| `target_kind` (T2) | `response_consumer_methods`, `exception_classes`, `module_level_functions`, `auth_classes`, `adapter_methods`, `prepare_methods`, `context_manager_pair`, `proxy_utils`, ... |
| `answer_entries`   | 2 – 13                                                                                                        |
| `answer_files`     | 1 – 6                                                                                                         |
| `unique_trait`     | free-form; e.g. `decorated_anchor`, `nested_def_present`, `name_collision`, `same_file_fanin`, `cluster_<name>` |

Run the proposer with `--tier <tier>` and read the predicted signatures for
existing slots. When the matrix runs out of room (all tuples used), switch
template or scope before forcing a duplicate through.

## 6. Pilot panel + automated acceptance

Once a new sample is registered and audits pass, run the full panel to check
difficulty gradient and structural diversity:

```bash
./c.sh    # iterates 5 models × 3 seeds × all IDs in the loop
```

Then run the analyzer, which drives off every `runs/v1/*/*/scores.json`,
uses the most-recent `--seeds-per-model` trials per `(model, sample)`, and
emits both the correlation matrix and the per-model tier pass-rate table:

```bash
python3 data/scripts/analyze_localization_panel.py --ids 21-50
# or dump everything as JSON for a downstream tool
python3 data/scripts/analyze_localization_panel.py --ids 21-50 --json \
  > analysis/panel_snapshot.json
```

The acceptance criteria:

* **Same-tier clone check** — no same-tier pair has Pearson ≥ 0.85 on its
  binary pass/fail vector across the panel. If a pair trips the threshold,
  redesign one by switching template, scope shape, or `unique_trait`.
* **Difficulty-gradient check** — for every model,
  `pass_rate(easy) >= pass_rate(medium) >= pass_rate(hard)`. An inversion
  usually indicates either a mis-tagged sample (override the `difficulty`
  label with a written justification in the manifest note) or a structural
  pick that ended up easier than intended (move it to a lower tier and
  re-balance with a tougher replacement at the original tier).

The analyzer tolerates partial panels — it prints trial counts per sample
so you can tell whether a correlation flag is real or statistical noise
from thin coverage. As a rule of thumb you want ≥ 9 trials per sample
before trusting a correlation flag, and ≥ 3 trials × (tier size) before
trusting a gradient violation.

## 7. Porting to a new repo

The oracle currently assumes the `requests` repo is mounted at
`projects/v1/requests`. To target a different repo:

1. Register it in [data/v1_repos.json](../../v1_repos.json) with its
   canonical URL, pinned commit SHA, and submodule path.
2. Add the submodule at that path and `git submodule update --init`.
3. Generalize `V1_REQUESTS_ROOT` in
   [data/scripts/localization_oracle.py](../localization_oracle.py) to a
   parametrizable constant (or switch to a dict indexed by repo name), then
   plumb a `--repo` flag through the proposer and scorer (they both already
   take `--repo`, but currently only `requests` is wired).
4. Smoke-test:

   ```bash
   python3 data/scripts/propose_localization_candidates.py \
     --repo <new_repo> --scope <src_dir> --top 5 --validate
   ```

   A 10-minute onboarding check: every top-5 candidate should validate.

## 8. Known gotchas

* **Nested-def attribution.** A call site physically inside a nested `def`
  counts toward the *enclosing* function too. The nested function is *also*
  a separate entry in its own right. The T2 prompt template already spells
  this out; keep it when generating new prompts or Claude-sized models will
  miscount the enclosing function.
* **Exclusion by name (T2 only).** A function whose own unqualified name
  equals one of the target names is excluded from the answer, regardless of
  class or module. The T2 prompt template spells this out explicitly — keep
  the wording verbatim.
* **Import aliases.** The oracle resolves calls by bare callee name, so
  `import requests.adapters as ra; ra.cert_verify(...)` would be attributed
  to `cert_verify` via its attribute name. Mostly works; if you see a
  puzzling derived entry, grep for aliased imports and confirm.
* **Decorators.** The oracle rejects decorated T1 anchors by default. Pass
  `"allow_decorators": true` in the candidate stub (and set
  `anchor_kind` accordingly) only when the decorator doesn't change the
  callable semantics (`@property` is the common case).
* **Async defs.** Treated like regular defs for call attribution, but the
  anchor/caller list will flip into the `async_method` bucket, which
  counts as a trap and bumps the tier to hard automatically. Usually what
  you want.
* **`__all__` re-exports.** Not followed. The oracle only looks at
  definitions; a re-export at the package root never produces an entry.
  This can surprise you if you expect `requests.adapters` calls through
  the `requests` shim to attribute — they don't.
* **Caller body contains both a bare call and an attribute call.** Both
  match; the AST call-site list will have both line numbers, but the
  caller is still one entry.

## 9. When the proposer runs dry

If the proposer returns zero candidates for a tier you need:

* Widen the scope (e.g. from `src/requests/cookies.py` to
  `src/requests/`).
* Relax the proposer knobs: `--top 30`, `--include-decorated`,
  `--template T2`.
* Mine more seed clusters — extend the `_cluster_seeds()` list in
  `data/scripts/propose_localization_candidates.py` with new thematic groups
  specific to the repo.
* As a last resort, add a new `unique_trait` dimension (e.g.
  `test_scope_includes_tests_dir`) and expand the matrix, but only after
  exhausting the existing knobs.

## 10. Checklist for the agent

When generating N samples end-to-end, the agent should:

```text
for each new sample:
  1. run the proposer for the desired tier
  2. pick a candidate whose structural tuple is unique
  3. write a stub to /tmp/cand.json
  4. run the scorer → must exit 0, signature_collisions == []
  5. append manifest entry (id, difficulty, signature, prompt_*)
  6. create data/scripts/derive_0NN_ground_truth.py (4 lines)

then once:
  7. python3 data/scripts/regen_structured_samples.py
  8. python3 data/scripts/audit_localization_structured.py  # must PASS
  9. update c.sh to iterate new IDs
  10. kick off the pilot panel
```
