# v1 code-review lock-in record (#91-#100, paper-faithful rebuild)

This is the freeze artifact for the **paper-faithful** `review_judgment` category, rebuilt from scratch per Ma et al. arXiv:2604.05013 Appendix E. The agent acts as a code reviewer (NOT a patch author): given a PR description + PR diff, it explores the repo in plan mode (read-only) and emits a structured `<judgment>YES|NO</judgment>` plus a `<review>` summary.

The single source of truth is [data/scripts/json/v1_review_criteria.json](../json/v1_review_criteria.json), which references [data/scripts/json/v1_editing_criteria.json](../json/v1_editing_criteria.json) entries `#51`-`#60` for the underlying bugs and patches. No new bugs are authored in this category.

Pinned to `requests` submodule pin `79f4df84cf77a2fee873809821dfbd786de05b97`.

## Authoring + audit timeline

| Phase | Status | Artifact |
|---|---|---|
| Phase 1 — infrastructure rewrite | DONE | [data/scripts/regen_review.py](../regen_review.py), [data/scripts/audit_review.py](../audit_review.py); deleted obsolete `data/v1_review_voice_corpus.md` |
| Phase 2 — source picks + 5 mutants | DONE | 5 mutants authored in [data/scripts/json/v1_editing_criteria.json](../json/v1_editing_criteria.json) (#52, #54, #56, #58, #60); 10 manifest entries drafted; all 10 labels verified by Pass-1 oracle |
| Phase 3 — regen + audit | DONE | 10 specs at `data/specs/v1/{091..100}_pr_review_*.md`; 10 rows in [data/samples_v1.jsonl](../../samples_v1.jsonl); audit Pass-1 + Pass-2 PASS |
| Phase 4 — pilot panel | LAUNCHER STAGED ([r.sh](../../../r.sh)); actual run requires network access from the user's bench environment | log in `runs/v1/<model>/<timestamp>/` after `bash r.sh` |
| Phase 5 — lock-in (this document) | DONE (offline portions); pilot history pending | this file + manifest hashes below |

## Per-sample lock-in hashes

`SHA-256(JSON-serialized {source_manifest, source_id, variant, label, issue_text})` for each manifest entry, sorted by id. Reproducible via the snippet at the bottom of this file.

| ID | Name | Variant | Label | SHA-256 |
|---|---|---|---|---|
| #91 | `pr_review_iter_slices_yes` | `reference_edit` | **YES** | `8cbbb3494303554308cc4edbcbff5dd4e5d27ee47899e5116c633770dacee945` |
| #92 | `pr_review_unicode_is_ascii_no` | `mutants[0]` | **NO** | `93ac9b5c99d661dce64b6cd5cb1765b63b3ae6c890f806457818169bf60a5a02` |
| #93 | `pr_review_to_native_string_yes` | `reference_edit` | **YES** | `7caee40a225363cf5f4776cb2784f2773fd2c4368367c7aa16bbbfd81ae661d8` |
| #94 | `pr_review_unquote_header_value_no` | `mutants[0]` | **NO** | `4120664a2d40093ad1f93bcef60bdc5ed547bd75a0bab543fc9d4fcc0ea899e8` |
| #95 | `pr_review_parse_header_links_yes` | `reference_edit` | **YES** | `c821718882796d806202e6a116ceb6d9af83722720a60b454385a7545c56483f` |
| #96 | `pr_review_is_ipv4_address_no` | `mutants[0]` | **NO** | `62b6749e87b55fb79bf38d6c41f6469c335577cda177457c6ad158b3308b4429` |
| #97 | `pr_review_is_valid_cidr_yes` | `reference_edit` | **YES** | `611e0e05a449e1e8a9a04e5c16cf8e37d8c87dba07f9dc40b1477314358678fb` |
| #98 | `pr_review_default_hooks_no` | `mutants[0]` | **NO** | `8156555a6a067a24bba5ad6c254b14d19f9304b8c27c3b725916f8918eddd583` |
| #99 | `pr_review_dispatch_hook_yes` | `reference_edit` | **YES** | `c1f9f234d799fa5e7231d00ce313bd9487540ce2da41e6482461c231632a496b` |
| #100 | `pr_review_address_in_network_no` | `mutants[0]` | **NO** | `bd48351bf018b11b2d20ac4c07f12b87c20c85b03dc925ef08e04b8414d2a1b1` |

## Source-to-sample mapping

5 YES + 5 NO. Each `#51`-`#60` source bug appears in exactly one review sample, with one variant (no signal leak across samples).

| New ID | Source bug | Variant | Label | Multi-file |
|---|---|---|---|---|
| #91 | `#51` `iter_slices` | `reference_edit` | YES | no |
| #92 | `#52` `unicode_is_ascii` | `mutants[0]` (any-vs-all) | NO | no |
| #93 | `#53` `to_native_string + caller` | `reference_edit` | YES | yes (2 files) |
| #94 | `#54` `unquote_header_value` | `mutants[0]` (return None vs '') | NO | no |
| #95 | `#55` `parse_header_links` | `reference_edit` | YES | no |
| #96 | `#56` `is_ipv4_address` | `mutants[0]` (inverted guard) | NO | no |
| #97 | `#57` `is_valid_cidr` | `reference_edit` | YES | no |
| #98 | `#58` `default_hooks` | `mutants[0]` (extra const, list unchanged) | NO | no |
| #99 | `#59` `dispatch_hook + caller` | `reference_edit` | YES | yes (2 files) |
| #100 | `#60` `address_in_network + caller` | `mutants[0]` (only adapters.py edit) | NO | yes (1 of 2 files patched) |

## Diversity gates

Lighter than the previous review_judgment category since variation here is structural (label, source) rather than semantic (bug class):

- G1 distinct source IDs across all 10 samples — PASS (10 distinct: #51-#60 each appear once)
- G2 5 YES + 5 NO label balance — PASS
- G3 ≥ 5 distinct source files — PASS (8 distinct paths inherited from `#51`-`#60`)

## Authored mutants summary (added to source manifest in Phase 2)

For sources whose `mutants[]` was empty, Phase 2 authored one mutant each. Each was mechanically validated: applied to baseline, exec_assert FAILS at least one assert from the source's truth table.

| Source | Mutant pattern | Asserts that fail | Misstep tag |
|---|---|---|---|
| #52 | `any` instead of `all` for the bytes-branch ASCII reduction | the high-byte sequence assert | `partial-edit` |
| #54 | return `None` instead of `''` for the None-input early-return | the `== ''` regression asserts | `partial-edit` |
| #56 | guard inverted (returns False on `str`, falls through on non-str) | the basic `'192.168.1.1' is True` regression | `partial-edit` |
| #58 | adds `REQUEST_EVENT = "request"` constant but leaves `HOOKS = ["response"]` unchanged | every `'request' in default_hooks()` and `len() == 2` assert | `partial-edit` |
| #60 | applies only the adapters.py edit (`_proxy_target_in_network`); leaves utils.py baseline | `address_in_network('not-an-ip', ...)` asserts (raises OSError, escapes) | `partial-edit` |

## Mechanical audit state (last verified)

```text
Pass 1 - in-process label oracle
  PASS #91-#100 (all labels mechanically derived from exec_assert against source truth tables)

Pass 2 - end-to-end through eval.py
  PASS #91-#100 (positive trace passes all 4 checks; 4 negative variants each fail their target check)

RESULT: PASS (10 samples validated)
```

Re-verify any time with `python3 data/scripts/audit_review.py`.

## Layer D (pilot panel) status

Pending. The launcher script [r.sh](../../../r.sh) runs 5 models x 3 seeds against the entire category in plan mode (`run.py` auto-injects `--agent plan` from each row's `agent: plan` field). Total: 150 model invocations.

Healthy-pattern criteria:

- claude / super pass ≥ 7/10 samples on the majority of seeds (solvable)
- at least one weaker model passes ≥ 3/10 samples (not impossibly hard)
- no sample is 0/15 across all model+seed combinations (label likely wrong; rerun mechanical audit before iterating)
- no sample is 15/15 (issue text too explicit; tighten paraphrasing)

Iteration contract: edit ONLY `issue_text` for any failing sample. NEVER modify the source manifest, the variant selection, or the label. Cap at 2 iterations per sample. After each iteration, that sample's lock-in hash changes; update the table above.

Append a `### Pilot run YYYY-MM-DD` subsection below as data arrives.

### Pilot run 2026-04-26 (initial v2 panel, 150/150 runs)

| ID | label | claude (3) | minimax (3) | nano (3) | super (3) | qwen3 (3) | total | verdict |
|---|---|---|---|---|---|---|---|---|
| 91 | YES | 3 | 3 | 3 | 2 | 3 | 14/15 | EASY (borderline) |
| 92 | NO | 3 | 2 | 1 | 3 | 3 | 12/15 | OK |
| 93 | YES | 3 | 2 | 2 | 1 | 0 | 8/15 | OK |
| 94 | NO | 3 | 2 | 1 | 1 | 2 | 9/15 | OK |
| 95 | YES | 3 | 3 | 2 | 3 | 2 | 13/15 | OK |
| 96 | NO | 3 | 1 | 3 | 0 | 1 | 8/15 | OK |
| 97 | YES | 3 | 3 | 3 | 1 | 3 | 13/15 | OK |
| 98 | NO | 3 | 3 | 3 | 1 | 3 | 13/15 | OK |
| 99 | YES | 3 | 1 | 3 | 0 | 0 | 7/15 | OK |
| 100 | NO | 3 | 0 | 1 | 0 | 3 | 7/15 | OK |

Per-model:

| Model | Pass-rate | Bar |
|---|---|---|
| claude-opus-4-6 | **30/30 (100%)** | `##############################` |
| nemotron-3-nano-30b-a3b | 22/30 (73%) | `######################........` |
| minimax-m2.5 | 20/30 (67%) | `####################..........` |
| qwen3-next-thinking | 20/30 (67%) | `####################..........` |
| nemotron-3-super-120b-a12b | 12/30 (40%) | `############..................` |

Failure-mode breakdown (failures occurrences across 150 runs):

| Model | plan_violation | judgment_wrong | review_missing | schema_bad | other |
|---|---|---|---|---|---|
| claude | 0 | 0 | 0 | 0 | 0 |
| minimax | 1 | 5 | 8 | 0 | 1 |
| nano | 1 | 8 | 6 | 1 | 0 |
| super | 10 | 8 | 12 | 0 | 0 |
| qwen3 | 0 | 8 | 9 | 0 | 0 |

#### Headline: model ranking inverted vs tools-mode

The same models score in a completely different order in plan mode vs the tools-mode tasks (`#21` v3b, `#51`-`#60`, the deleted comment-to-fix `#91`-`#100`):

| Tools-mode rank | Plan-mode rank (this category) |
|---|---|
| 1. claude | 1. claude |
| 2. super | 2. **nano** |
| 3. minimax / qwen3 | 3. minimax / qwen3 (tied) |
| 4. nano | 4. **super** |

Super's bash-driven self-verification strategy is structurally incompatible with plan mode (10 of its 18 failures are direct plan-mode violations: `bash` calls). Nano's tools-mode floor was driven by tool-call hygiene problems (bash schema, stale-path reads) that are simply absent in plan mode where nano doesn't need to use those tools.

#### Lock-in decision

All 10 samples land in OK or borderline-EASY band. **No iteration of `issue_text` required.** The category cleanly discriminates:

- claude (top tier, 100%)
- nano / minimax / qwen3 (mid tier, 67-73%)
- super (floor, 40%)

#### Discriminating samples

Hardest: `#99` and `#100` (7/15 each), both multi-file PRs. `#99` is a YES (qwen3 + super both missed verifying the second file in 3/3 seeds). `#100` is a NO with the partial-edit mutant (minimax + super both said YES). Multi-file samples discriminate strongly, as expected.

Easiest: `#91` (14/15, single-file YES with simple fix). Borderline EASY — the only failure was super violating plan mode, so the sample is still doing real work at this difficulty level. Not iterated.

## Reproducing the hashes

```python
import json, hashlib
from pathlib import Path

manifest = json.loads(Path("data/v1_review_criteria.json").read_text())
for s in manifest["samples"]:
    payload = {
        "source_manifest": s["source_manifest"],
        "source_id": s["source_id"],
        "variant": s["variant"],
        "label": s["label"],
        "issue_text": s["issue_text"],
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    print(f"#{s['id']:<3} {hashlib.sha256(blob).hexdigest()}")
```

## Plan-mode coverage signal

Adding `#91`-`#100` to the bench raises the plan-mode footprint considerably:

| Before this rebuild | After this rebuild |
|---|---|
| 2 plan-mode samples (`#1`, `#2`) out of 50 v1 samples | 12 plan-mode samples (`#1`, `#2`, `#91`-`#100`) out of 60 v1 samples |
| 4% of v1 surface | 20% of v1 surface |

The `review_judgment` category alone now covers structured-judgment + plan-mode adherence + read-only deliberation across 10 samples, which is the opencode skill `#1` and `#2` originally hinted at but couldn't measure at scale.

## Cross-references

- Spec files: `data/specs/v1/091_pr_review_*.md` through `data/specs/v1/100_pr_review_*.md`
- Manifest: [data/scripts/json/v1_review_criteria.json](../json/v1_review_criteria.json)
- Source manifest (cross-referenced): [data/scripts/json/v1_editing_criteria.json](../json/v1_editing_criteria.json)
- Authoring pipeline: [data/scripts/regen_review.py](../regen_review.py)
- Audit pipeline: [data/scripts/audit_review.py](../audit_review.py)
- Pilot launcher: [r.sh](../../../r.sh)
- JSONL rows: rows with `id` 91-100 in [data/samples_v1.jsonl](../../samples_v1.jsonl)
- Paper: Ma et al., arXiv:2604.05013, Appendix E
