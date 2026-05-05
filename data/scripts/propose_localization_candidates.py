#!/usr/bin/env python3
"""
Propose v3c localization-sample candidates for a pinned repo.

Produces two ranked candidate lists from the AST of a scope:

* T1 (anchor + direct callers) — every function with a workable number of
  direct callers in scope.
* T2 (callers of a set) — thematic clusters mined from name prefixes /
  suffixes / dunder pairs / hand-seeded seeds, scored by caller fan-out.

Each candidate includes:

* a predicted `difficulty` tier (easy / medium / hard) derived from a
  simple heuristic matching the convention in
  `data/v1_localization_criteria.json`;
* a predicted `structural_signature` stub to check tuple-uniqueness against
  existing entries.

Candidates whose anchor / target set is already used by an existing sample
in `data/v1_localization_criteria.json` are filtered out. Candidates whose
predicted structural signature collides with an existing entry are kept but
flagged (the sample designer may still want to keep them with a different
`unique_trait` that distinguishes them).

Output is JSON to stdout by default (or `--output <path>`). The shape is
intended to be machine-readable for follow-up scoring via
`data/scripts/score_localization_candidate.py` and human-readable for a quick
skim.

Usage
-----
    python3 data/scripts/propose_localization_candidates.py --repo requests \
        --scope src/requests --top 15

    python3 data/scripts/propose_localization_candidates.py --repo requests \
        --scope src/requests --tier hard --include-decorated

    # Machine-readable: pipe into the scorer
    python3 data/scripts/propose_localization_candidates.py --repo requests \
        --scope src/requests --top 5 --tier medium --format json \
        > /tmp/proposals.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.scripts.localization_oracle import (  # noqa: E402
    FuncAnalysis,
    analyze_scope,
    anchor_and_callers,
    callers_of_set,
)

MANIFEST_PATH = ROOT / "data" / "scripts" / "json" / "v1_localization_criteria.json"

# Minimum / maximum answer size for a viable T1 anchor.
T1_MIN_CALLERS = 1   # anchor itself is entry 1, so 1 direct caller => 2 entries
T1_MAX_CALLERS = 11  # cap at 12 entries total
# T1 candidates should produce at least 2 entries total (anchor + 1 caller).
T1_MIN_TOTAL_ENTRIES = 2

# T2 bounds -- a target set must cover a meaningful fan-out without being
# trivial (set-of-one collapses to T1) or overwhelming.
T2_MIN_ENTRIES = 3
T2_MAX_ENTRIES = 14
T2_MIN_TARGETS = 2
T2_MAX_TARGETS = 6


# ---------------------------------------------------------------------------
# Existing-sample index (so we don't re-propose something we already have)
# ---------------------------------------------------------------------------


def load_manifest() -> list[dict[str, Any]]:
    return json.loads(MANIFEST_PATH.read_text()).get("samples", [])


def existing_anchors(manifest: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """Return set of (file, name) pairs already used as T1 anchors."""
    return {
        (e["anchor"]["file"], e["anchor"]["name"])
        for e in manifest
        if e.get("template") == "T1" and "anchor" in e
    }


def existing_target_sets(manifest: list[dict[str, Any]]) -> list[set[str]]:
    return [
        set(e["targets"]) for e in manifest
        if e.get("template") == "T2" and "targets" in e
    ]


def existing_signatures(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e.get("structural_signature", {}) for e in manifest]


# ---------------------------------------------------------------------------
# Difficulty heuristic (matches the playbook)
# ---------------------------------------------------------------------------


def _trap_count(traits: dict[str, Any]) -> int:
    return sum(
        1 for k in (
            "has_nested_def",
            "name_collision",
            "decorator",
            "async",
            "import_alias",
        )
        if traits.get(k)
    )


def predict_difficulty(n_entries: int, n_files: int, traits: dict[str, Any]) -> str:
    """Match the heuristic in `data/scripts/docs/building_localization_samples.md`.

    Easy    if entries <= 3 AND files <= 2 AND no traps
    Hard    if entries >= 7 OR files >= 4 OR >= 1 traps
    Medium  otherwise
    """
    traps = _trap_count(traits)
    if n_entries <= 3 and n_files <= 2 and traps == 0:
        return "easy"
    if n_entries >= 7 or n_files >= 4 or traps >= 1:
        return "hard"
    return "medium"


def scope_kind_for(n_files: int) -> str:
    if n_files <= 1:
        return "single_file"
    if n_files == 2:
        return "two_files"
    if n_files == 3:
        return "three_files"
    if n_files == 4:
        return "four_files"
    return "any_file"


# ---------------------------------------------------------------------------
# T1 proposals
# ---------------------------------------------------------------------------


@dataclass
class T1Candidate:
    anchor_file: str
    anchor_name: str
    anchor_qualname: str
    anchor_kind: str
    scope: list[str]
    predicted_entries: int
    predicted_files: int
    predicted_difficulty: str
    structural_signature: dict[str, Any]
    score: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build_callers_index(analyses: list[FuncAnalysis]) -> dict[str, list[FuncAnalysis]]:
    """Map callee bare name -> list of callers that invoke that name."""
    out: dict[str, list[FuncAnalysis]] = defaultdict(list)
    for a in analyses:
        for cand_name in set(a.call_names):
            out[cand_name].append(a)
    return out


def propose_t1(
    analyses: list[FuncAnalysis],
    *,
    include_decorated: bool,
    exclude_anchors: set[tuple[str, str]],
    used_signatures: list[dict[str, Any]],
) -> list[T1Candidate]:
    """Enumerate every function whose direct-caller count in scope is sane."""
    callers_idx = _build_callers_index(analyses)
    # Index per-name occurrences so we can detect ambiguity (two funcs with
    # the same bare name across files); those make bad T1 anchors because the
    # caller attribution becomes ambiguous.
    name_counts = defaultdict(int)
    for a in analyses:
        name_counts[a.info.name] += 1

    out: list[T1Candidate] = []
    for a in analyses:
        fi = a.info
        if (fi.file, fi.name) in exclude_anchors:
            continue
        # Ambiguous name (multiple defs of the same bare name anywhere in
        # scope) -> skip, or there would be two "which anchor is it?" picks.
        if name_counts[fi.name] > 1:
            continue
        if a.has_decorator and not include_decorated:
            # Decorators are skipped unless explicitly opted in -- the oracle
            # allow_decorators flag is off by default.
            continue
        callers = [
            c for c in callers_idx.get(fi.name, [])
            if c.info.entry != fi.entry
        ]
        if not (T1_MIN_CALLERS <= len(callers) <= T1_MAX_CALLERS):
            continue

        caller_files = {c.info.file for c in callers}
        scope_files = sorted(caller_files | {fi.file})
        n_entries = 1 + len(callers)
        n_files = len(scope_files)
        if n_entries < T1_MIN_TOTAL_ENTRIES:
            continue

        traits = {
            "has_nested_def": a.has_nested_def or any(c.has_nested_def for c in callers),
            "async": a.is_async or any(c.is_async for c in callers),
            "decorator": a.has_decorator,
            "name_collision": False,  # filtered above
            "import_alias": False,
        }
        difficulty = predict_difficulty(n_entries, n_files, traits)

        sig = {
            "template": "T1",
            "scope_kind": scope_kind_for(n_files),
            "anchor_kind": a.anchor_kind,
            "answer_entries": n_entries,
            "answer_files": n_files,
            "unique_trait": _guess_unique_trait(a, callers, traits),
        }

        # Interestingness score: prefer cross-file spread, moderate sizes,
        # non-dunder names (public API surface is more descriptive).
        score = 0.0
        score += len(caller_files) * 1.5           # cross-file spread
        score += min(len(callers), 6) * 1.0        # moderate size
        if not fi.name.startswith("_"):
            score += 0.5
        if a.anchor_kind != "module_level":
            score += 0.3                           # reward diversity away from module_level
        # Penalize huge answers slightly (hard tier has only 6 slots).
        if n_entries > 10:
            score -= 1.0
        # Penalize if signature tuple exactly matches an existing entry.
        if _sig_collides(sig, used_signatures):
            score -= 0.8

        out.append(T1Candidate(
            anchor_file=fi.file,
            anchor_name=fi.name,
            anchor_qualname=fi.qualname,
            anchor_kind=a.anchor_kind,
            scope=scope_files,
            predicted_entries=n_entries,
            predicted_files=n_files,
            predicted_difficulty=difficulty,
            structural_signature=sig,
            score=round(score, 2),
            notes=[
                f"decorators={list(a.decorator_names)}" if a.has_decorator else "",
                f"has_nested_def=True" if traits["has_nested_def"] else "",
                f"async=True" if traits["async"] else "",
            ],
        ))
    out.sort(key=lambda c: c.score, reverse=True)
    return out


def _guess_unique_trait(a: FuncAnalysis, callers: list[FuncAnalysis], traits: dict[str, Any]) -> str:
    parts = []
    caller_files = {c.info.file for c in callers}
    caller_classes = {c.info.class_chain[0] for c in callers if c.info.class_chain}
    if traits["has_nested_def"]:
        parts.append("nested_def_present")
    if traits["decorator"]:
        parts.append(f"decorated_{a.anchor_kind}")
    if traits["async"]:
        parts.append("async_call_site")
    if len(caller_files) >= 3:
        parts.append(f"fanout_across_{len(caller_files)}_files")
    if len(caller_classes) >= 2:
        parts.append(f"callers_in_{len(caller_classes)}_classes")
    if not parts:
        if a.anchor_kind == "module_level" and caller_classes:
            parts.append("module_level_anchor_with_method_callers")
        elif a.anchor_kind == "instance_method" and len(caller_files) == 1:
            parts.append("same_file_method_fanin")
        else:
            parts.append(f"{a.anchor_kind}_generic")
    return "__".join(parts)


def _sig_collides(sig: dict[str, Any], used: list[dict[str, Any]]) -> bool:
    """Return True if `sig` matches any used signature on the tuple
    (template, scope_kind, anchor_kind|target_kind, answer_entries, answer_files)
    -- ignoring `unique_trait` which we expect the designer to differentiate.
    """
    keys = ("template", "scope_kind", "answer_entries", "answer_files")
    kind_key = "anchor_kind" if sig["template"] == "T1" else "target_kind"
    for u in used:
        if u.get("template") != sig["template"]:
            continue
        if all(u.get(k) == sig.get(k) for k in keys) and u.get(kind_key) == sig.get(kind_key):
            return True
    return False


# ---------------------------------------------------------------------------
# T2 proposals (clustered target sets)
# ---------------------------------------------------------------------------


@dataclass
class T2Candidate:
    targets: list[str]
    scope: list[str]
    target_kind: str
    cluster_rationale: str
    predicted_entries: int
    predicted_files: int
    predicted_difficulty: str
    structural_signature: dict[str, Any]
    score: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cluster_seeds() -> list[tuple[str, str, list[str]]]:
    """Hand-seeded thematic target clusters we want to try.

    (cluster_name, target_kind, target_names)
    """
    return [
        ("auth_classes", "auth_classes", ["AuthBase", "HTTPBasicAuth", "HTTPProxyAuth", "HTTPDigestAuth"]),
        ("adapter_methods", "adapter_methods", ["send", "close", "build_response", "get_connection_with_tls_context", "cert_verify"]),
        ("prepare_methods", "prepare_methods", ["prepare", "prepare_method", "prepare_url", "prepare_headers", "prepare_body", "prepare_auth", "prepare_cookies", "prepare_hooks"]),
        ("context_manager_pair", "context_manager_pair", ["__enter__", "__exit__"]),
        ("utils_parse", "module_level_functions", ["parse_header_links", "parse_list_header", "parse_dict_header", "_parse_content_type_header"]),
        ("utils_get", "module_level_functions", ["get_auth_from_url", "get_netrc_auth", "get_encoding_from_headers", "get_unicode_from_response", "get_encodings_from_content"]),
        ("utils_resolve_proxy", "module_level_functions", ["resolve_proxies", "select_proxy", "should_bypass_proxies"]),
        ("utils_check", "module_level_functions", ["check_compatibility", "check_header_validity", "_check_cryptography"]),
        ("iter_utils", "module_level_functions", ["stream_decode_response_unicode", "iter_slices"]),
        ("cookie_utils", "module_level_functions", ["cookiejar_from_dict", "extract_cookies_to_jar", "create_cookie", "get_cookie_header", "remove_cookie_by_name"]),
        ("prepared_access", "model_accessors", ["path_url", "cookies"]),
    ]


def _prefix_clusters(analyses: list[FuncAnalysis], *, min_size: int = 3, max_size: int = 6) -> list[tuple[str, str, list[str]]]:
    """Mine module-level functions by shared name prefix (e.g. `parse_*`)."""
    # Group by first underscore-separated word.
    buckets: dict[str, list[FuncAnalysis]] = defaultdict(list)
    for a in analyses:
        fi = a.info
        if a.anchor_kind != "module_level":
            continue
        if fi.name.startswith("_"):
            continue
        parts = fi.name.split("_", 1)
        if len(parts) < 2 or not parts[0]:
            continue
        buckets[parts[0]].append(a)
    out = []
    for prefix, mems in buckets.items():
        if not (min_size <= len(mems) <= max_size):
            continue
        names = sorted({m.info.name for m in mems})
        out.append((f"prefix_{prefix}_star", "module_level_functions", names))
    return out


def propose_t2(
    analyses: list[FuncAnalysis],
    *,
    exclude_sets: list[set[str]],
    used_signatures: list[dict[str, Any]],
) -> list[T2Candidate]:
    """Score each seed cluster + prefix-mined cluster against the scope."""
    name_to_analysis = {a.info.qualname: a for a in analyses}
    all_names_in_scope = {a.info.name for a in analyses}

    clusters = _cluster_seeds() + _prefix_clusters(analyses)

    # Map bare name -> set of files where callers reference it
    name_caller_files: dict[str, set[str]] = defaultdict(set)
    name_callers: dict[str, set[str]] = defaultdict(set)  # caller entries
    for a in analyses:
        for called in set(a.call_names):
            name_caller_files[called].add(a.info.file)
            name_callers[called].add(a.info.entry)

    out: list[T2Candidate] = []
    for cname, target_kind, targets in clusters:
        # Ignore clusters whose targets aren't present in scope (the names
        # may come from other modules; we only want callable targets we can
        # statically verify).
        in_scope = [t for t in targets if t in all_names_in_scope]
        if not (T2_MIN_TARGETS <= len(in_scope) <= T2_MAX_TARGETS):
            continue

        # Skip exact duplicates of an existing sample's target set.
        target_set = set(in_scope)
        if any(target_set == s for s in exclude_sets):
            continue

        # Count callers that invoke ANY target in this cluster, excluding
        # anything whose own name is also a target (matches oracle rule).
        caller_entries: set[str] = set()
        caller_files: set[str] = set()
        for t in in_scope:
            for entry in name_callers.get(t, set()):
                fi_qual = entry.split("::", 1)[1]
                # Exclude functions whose own bare name is itself a target.
                a = name_to_analysis.get(fi_qual)
                if a is None:
                    continue
                if a.info.name in target_set:
                    continue
                caller_entries.add(entry)
                caller_files.add(a.info.file)

        n_entries = len(caller_entries)
        n_files = len(caller_files)
        if not (T2_MIN_ENTRIES <= n_entries <= T2_MAX_ENTRIES):
            continue

        # Scope: for T2 we default to the whole src/requests directory (the
        # "any_file" kind). Passing as a trailing-slash string makes the
        # oracle's `_normalize_scope` expand it to all .py files.
        scope = ["src/requests/"]

        # Traits: is any caller in a nested closure? any rely on attribute calls?
        any_nested = any(
            name_to_analysis[e.split("::", 1)[1]].has_nested_def
            for e in caller_entries
            if e.split("::", 1)[1] in name_to_analysis
        )
        # Note: the "exclusion-by-name" rule always applies to T2, but we don't
        # count it as a difficulty trap unless one of the targets' bare names
        # actually collides with a non-target function def in scope (otherwise
        # the rule is vacuous).
        collision = any(
            t in all_names_in_scope
            and any(
                a.info.name == t and a.info.qualname.split(".", 1)[0] != t
                for a in analyses
            )
            for t in in_scope
        )
        traits = {
            "has_nested_def": any_nested,
            "name_collision": collision,
            "async": False,
            "decorator": False,
            "import_alias": False,
        }
        difficulty = predict_difficulty(n_entries, n_files, traits)

        sig = {
            "template": "T2",
            "scope_kind": "any_file",
            "target_kind": target_kind,
            "answer_entries": n_entries,
            "answer_files": n_files,
            "unique_trait": f"cluster_{cname}",
        }

        score = 0.0
        score += n_files * 1.2
        score += min(n_entries, 10) * 0.6
        score += len(in_scope) * 0.3
        if any_nested:
            score += 0.7
        if _sig_collides(sig, used_signatures):
            score -= 0.8

        out.append(T2Candidate(
            targets=in_scope,
            scope=scope,
            target_kind=target_kind,
            cluster_rationale=cname,
            predicted_entries=n_entries,
            predicted_files=n_files,
            predicted_difficulty=difficulty,
            structural_signature=sig,
            score=round(score, 2),
            notes=[f"cluster={cname}", f"targets_in_scope={in_scope}"],
        ))
    out.sort(key=lambda c: c.score, reverse=True)
    return out


# ---------------------------------------------------------------------------
# End-to-end validation for top picks (optional, --validate)
# ---------------------------------------------------------------------------


def _validate_t1(c: T1Candidate) -> str | None:
    try:
        r = anchor_and_callers(
            anchor_file=c.anchor_file,
            anchor_name=c.anchor_name,
            scope=c.scope,
            require_module_level_anchor=(c.anchor_kind == "module_level"),
            allow_decorators=c.anchor_kind in {"property", "classmethod", "staticmethod"},
        )
    except Exception as e:
        return f"derivation error: {e!r}"
    actual_entries = len(r.entries)
    actual_files = len({e.split("::", 1)[0] for e in r.entries})
    if actual_entries != c.predicted_entries:
        return f"entries mismatch: predicted {c.predicted_entries}, derived {actual_entries}"
    if actual_files != c.predicted_files:
        return f"files mismatch: predicted {c.predicted_files}, derived {actual_files}"
    return None


def _validate_t2(c: T2Candidate) -> str | None:
    # Proposer stores scope as a 1-element list with a trailing slash so the
    # oracle expands it as a directory; unwrap for the oracle call.
    scope: Any = c.scope[0] if len(c.scope) == 1 and c.scope[0].endswith("/") else c.scope
    try:
        r = callers_of_set(targets=c.targets, scope=scope)
    except Exception as e:
        return f"derivation error: {e!r}"
    actual_entries = len(r.entries)
    actual_files = len({e.split("::", 1)[0] for e in r.entries})
    if actual_entries != c.predicted_entries:
        return f"entries mismatch: predicted {c.predicted_entries}, derived {actual_entries}"
    if actual_files != c.predicted_files:
        return f"files mismatch: predicted {c.predicted_files}, derived {actual_files}"
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="requests", help="repo name (must be registered in data/v1_repos.json)")
    p.add_argument("--scope", default="src/requests", help="scope path (dir or file list)")
    p.add_argument("--top", type=int, default=12, help="max candidates per template per tier")
    p.add_argument("--tier", choices=["easy", "medium", "hard", "any"], default="any")
    p.add_argument("--template", choices=["T1", "T2", "both"], default="both")
    p.add_argument("--include-decorated", action="store_true",
                   help="allow T1 candidates whose anchor has decorators")
    p.add_argument("--validate", action="store_true",
                   help="re-run oracle on the top candidates to confirm counts match")
    p.add_argument("--format", choices=["json", "text"], default="text")
    p.add_argument("--output", type=Path, help="write to file instead of stdout")
    args = p.parse_args()

    if args.repo != "requests":
        print(
            f"ERROR: repo {args.repo!r} is not yet wired up. Register it in "
            f"data/v1_repos.json and update localization_oracle.py's "
            f"V1_REQUESTS_ROOT constant (or generalize it) before reusing.",
            file=sys.stderr,
        )
        return 2

    analyses = analyze_scope(args.scope)
    manifest = load_manifest()
    used_signatures = existing_signatures(manifest)
    exclude_anchors = existing_anchors(manifest)
    exclude_target_sets = existing_target_sets(manifest)

    t1: list[T1Candidate] = []
    t2: list[T2Candidate] = []
    if args.template in ("T1", "both"):
        t1 = propose_t1(
            analyses,
            include_decorated=args.include_decorated,
            exclude_anchors=exclude_anchors,
            used_signatures=used_signatures,
        )
    if args.template in ("T2", "both"):
        t2 = propose_t2(
            analyses,
            exclude_sets=exclude_target_sets,
            used_signatures=used_signatures,
        )

    if args.tier != "any":
        t1 = [c for c in t1 if c.predicted_difficulty == args.tier]
        t2 = [c for c in t2 if c.predicted_difficulty == args.tier]
    t1 = t1[: args.top]
    t2 = t2[: args.top]

    if args.validate:
        for c in t1:
            msg = _validate_t1(c)
            if msg:
                c.notes.append(f"VALIDATE FAIL: {msg}")
            else:
                c.notes.append("validated")
        for c in t2:
            msg = _validate_t2(c)
            if msg:
                c.notes.append(f"VALIDATE FAIL: {msg}")
            else:
                c.notes.append("validated")

    doc = {
        "repo": args.repo,
        "scope": args.scope,
        "tier_filter": args.tier,
        "template_filter": args.template,
        "n_t1": len(t1),
        "n_t2": len(t2),
        "candidates": {
            "T1": [c.to_dict() for c in t1],
            "T2": [c.to_dict() for c in t2],
        },
    }

    if args.format == "json":
        text = json.dumps(doc, indent=2)
    else:
        lines: list[str] = []
        lines.append(f"# Proposals for {args.repo} ({args.scope})")
        lines.append(f"# tier={args.tier}  template={args.template}  top={args.top}")
        lines.append("")
        if t1:
            lines.append(f"## T1 — {len(t1)} candidate(s)")
            for c in t1:
                lines.append(
                    f"  score={c.score:<5} [{c.predicted_difficulty:6}] "
                    f"{c.anchor_file}::{c.anchor_qualname:32} "
                    f"entries={c.predicted_entries}/files={c.predicted_files} "
                    f"kind={c.anchor_kind}"
                )
                if c.notes:
                    for n in c.notes:
                        if n:
                            lines.append(f"    - {n}")
            lines.append("")
        if t2:
            lines.append(f"## T2 — {len(t2)} candidate(s)")
            for c in t2:
                lines.append(
                    f"  score={c.score:<5} [{c.predicted_difficulty:6}] "
                    f"{c.cluster_rationale:32} "
                    f"entries={c.predicted_entries}/files={c.predicted_files} "
                    f"targets={c.targets}"
                )
                if c.notes:
                    for n in c.notes:
                        if n:
                            lines.append(f"    - {n}")
        text = "\n".join(lines) + "\n"

    if args.output:
        args.output.write_text(text)
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
