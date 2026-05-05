# v1 code-review diversity grid (`#91`-`#100`, paper-faithful)

This is the diversity view for the paper-faithful `code_review` category. The samples implement Ma et al. arXiv:2604.05013 Appendix E: PR-judgment in plan mode, with cross-referenced source material from the existing `code_editing` manifest.

Pinned to submodule pin `79f4df84cf77a2fee873809821dfbd786de05b97`.

## The grid

| ID | Source | Variant | Label | Difficulty | Multi-file | Target file(s) |
|---|---|---|---|---|---|---|
| 91 | `#51` `iter_slices` | `reference_edit` | YES | medium | no | `src/requests/utils.py` |
| 92 | `#52` `unicode_is_ascii` | `mutants[0]` | NO | medium | no | `src/requests/_internal_utils.py` |
| 93 | `#53` `to_native_string + caller` | `reference_edit` | YES | hard | yes (2 files) | `src/requests/_internal_utils.py`, `src/requests/auth.py` |
| 94 | `#54` `unquote_header_value` | `mutants[0]` | NO | medium | no | `src/requests/utils.py` |
| 95 | `#55` `parse_header_links` | `reference_edit` | YES | medium | no | `src/requests/utils.py` |
| 96 | `#56` `is_ipv4_address` | `mutants[0]` | NO | medium | no | `src/requests/utils.py` |
| 97 | `#57` `is_valid_cidr` | `reference_edit` | YES | medium | no | `src/requests/utils.py` |
| 98 | `#58` `default_hooks` | `mutants[0]` | NO | medium | no | `src/requests/hooks.py` |
| 99 | `#59` `dispatch_hook + caller` | `reference_edit` | YES | hard | yes (2 files) | `src/requests/hooks.py`, `src/requests/sessions.py` |
| 100 | `#60` `address_in_network + caller` | `mutants[0]` | NO | hard | yes (1 of 2 patched) | `src/requests/utils.py`, `src/requests/adapters.py` |

## Diversity gates

| Gate | Constraint | Result |
|---|---|---|
| G1 | Distinct source IDs across all 10 (no signal leak from same source appearing twice with different labels) | PASS — 10 distinct source IDs (`#51`-`#60` each appear once) |
| G2 | 5 YES + 5 NO label balance | PASS — exact 5/5 split |
| G3 | ≥ 5 distinct target files inherited from sources | PASS — 8 distinct paths: `utils.py`, `_internal_utils.py`, `auth.py`, `hooks.py`, `sessions.py`, `adapters.py` (counting paths involved in any sample's target set) |

## Label-balance + difficulty distribution

| Label | Count | IDs |
|---|---|---|
| YES | 5 | 91, 93, 95, 97, 99 |
| NO | 5 | 92, 94, 96, 98, 100 |

| Difficulty | Count | IDs |
|---|---|---|
| medium | 7 | 91, 92, 94, 95, 96, 97, 98 |
| hard | 3 | 93, 99, 100 |

| Multi-file | Count | IDs |
|---|---|---|
| no (single-file diff) | 7 | 91, 92, 94, 95, 96, 97, 98 |
| yes (2-file diff) | 3 | 93, 99, 100 |

## Why each pick

The 10 samples were chosen to give complete coverage of `#51`-`#60` (each source appears exactly once) while balancing YES/NO labels and including all three multi-file (hard-tier) sources. Each YES variant is the canonical reference edit; each NO variant is a hand-authored mutant that fails at least one assertion in the source's truth table.

### YES samples (5)

- **#91** uses `#51`'s reference fix (a single guard at the top of `iter_slices`). The agent reads `utils.py` and confirms the fix matches the issue.
- **#93** uses `#53`'s multi-file reference fix (a TypeError-with-substring in `_internal_utils.py` plus None-handling in `auth.py`'s `_basic_auth_str`). Two-file PR — the agent must verify both ends.
- **#95** uses `#55`'s reference fix to `parse_header_links` (skip empty-`url` entries).
- **#97** uses `#57`'s reference fix to `is_valid_cidr` (accept `/0` mask).
- **#99** uses `#59`'s multi-file reference fix (None-skip in `dispatch_hook` + new `apply_response_hooks` helper in `sessions.py`).

### NO samples (5)

Each authored mutant introduces a plausible-looking but incorrect fix:

- **#92** mutant: changes `all(b < 128 for b in u_string)` to `any(b < 128 for b in u_string)` — `b'h\xc3\xa9llo'` (mixed ASCII + non-ASCII) wrongly returns `True`.
- **#94** mutant: returns `None` instead of `''` for the None-input early-return — fails the `== ''` regression asserts.
- **#96** mutant: inverts the type guard (`if isinstance(string_ip, str): return False`) — every str input wrongly returns False.
- **#98** mutant: adds a stray `REQUEST_EVENT = "request"` module constant but leaves `HOOKS = ["response"]` unchanged — `default_hooks()` still returns a single-key dict.
- **#100** mutant: applies only the adapters.py portion of `#60`'s multi-file fix (the new `_proxy_target_in_network` helper), leaving the utils.py defensive `try/except` unmade — `address_in_network('not-an-ip', ...)` still raises.

## Comment-style note

Unlike the previous `code_review` design (comment-to-fix, mislabeled), this paper-faithful version doesn't use a "comment_style" axis — the prompt is a paper-prescribed PR-review template (Appendix E), not a hand-authored reviewer voice. All 10 samples share the same prompt frame, differing only in `issue_text` and `<pr_code>`.

## Phase-2 checkpoint

This grid was the deliverable for the Phase-2 checkpoint per the plan. The picks shown here were authored end-to-end in Phase 3, the mechanical audit was run in Phase 4, and the lock-in record (with per-sample SHA-256 hashes) lives in [data/scripts/docs/v1_review_lock_in.md](v1_review_lock_in.md). Phase 5 (pilot panel) launcher is staged at [r.sh](../../../r.sh).
