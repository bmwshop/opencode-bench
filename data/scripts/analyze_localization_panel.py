#!/usr/bin/env python3
"""
Compute per-tier Pearson correlation matrix + per-model difficulty-gradient
table for one of the v1 sample families.

Two families are supported via `--family`:

  * ``localization`` (default)    -- structured-output answer-shape samples
                                     (#21-#50, manifest
                                     ``data/v1_localization_criteria.json``,
                                     category ``code_localization``).
  * ``editing``                   -- de-leaked code-editing samples
                                     (#51-#60, manifest
                                     ``data/v1_editing_criteria.json``,
                                     category ``code_editing``).

Drives off the most recent 3 runs per `(model, sample_id)` under `runs/v1/`,
so it can be invoked while the pilot panel is still in flight and incrementally
report what has landed so far.

Outputs:
  * `analysis/panel_raw_YYYYMMDD_HHMMSS.json` -- per-(model, seed, sample)
    pass/fail (boolean) + difficulty tier.
  * A text summary to stdout with:
      - per-tier Pearson correlation matrix (samples x samples);
      - any same-tier pair with Pearson >= 0.85 (clones);
      - per-model pass-rate by tier (gradient monotonicity check);
      - sample coverage counts so you can tell when the panel is done.

Usage
-----
    # Localization (default).
    python3 data/scripts/analyze_localization_panel.py
    python3 data/scripts/analyze_localization_panel.py --models claude-opus-4-6 minimax-m2.5 \
        --ids 21-50 --seeds-per-model 3
    python3 data/scripts/analyze_localization_panel.py --json > /tmp/panel.json

    # Editing (#51-60 de-leaked samples).
    python3 data/scripts/analyze_localization_panel.py --family editing
    python3 data/scripts/analyze_localization_panel.py --family editing --json \\
        > analysis/editing_panel_snapshot.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "v1"

FAMILIES: dict[str, dict[str, Any]] = {
    "localization": {
        "manifest": ROOT / "data" / "v1_localization_criteria.json",
        "default_ids": "21-50",
        "category": "code_localization",
        "tier_field": "difficulty",
        "tier_order": ["easy", "medium", "hard"],
    },
    "editing": {
        "manifest": ROOT / "data" / "v1_editing_criteria.json",
        "default_ids": "51-80",
        "category": "code_editing",
        "tier_field": "difficulty",
        "tier_order": ["easy", "medium", "hard"],
    },
    "mutants": {
        "manifest": ROOT / "data" / "v1_mutant_criteria.json",
        "default_ids": "201-230",
        "category": "tool_restriction",
        # Tool-restriction samples now use explicit easy/medium/hard tiers.
        "tier_field": "difficulty",
        "tier_order": ["easy", "medium", "hard"],
    },
    "orchestration": {
        "manifest": ROOT / "data" / "v1_orchestration_criteria.json",
        "default_ids": "301-330",
        "category": "orchestration",
        # Orchestration samples are grouped by explicit easy/medium/hard tiers.
        "tier_field": "difficulty",
        "tier_order": ["easy", "medium", "hard"],
    },
    "skill": {
        "manifest": ROOT / "data" / "v1_skill_criteria.json",
        "default_ids": "401-430",
        "category": "skill",
        # Skill samples now use explicit easy/medium/hard tiers.
        "tier_field": "difficulty",
        "tier_order": ["easy", "medium", "hard"],
    },
}


def load_manifest(family: str) -> dict[int, dict[str, Any]]:
    path = FAMILIES[family]["manifest"]
    d = json.loads(path.read_text())
    return {s["id"]: s for s in d.get("samples", [])}


def parse_id_spec(spec: str) -> list[int]:
    """Expand `21-30,34,40` into a sorted list of ints."""
    out: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(chunk))
    return sorted(out)


def _scored_runs_with_family_data(
    model_dir: Path,
    sample_ids_set: set[int],
) -> list[Path]:
    """Return scored run dirs for this model that contain at least one
    completed sample whose id is in `sample_ids_set`.

    Mixed-category runs (e.g. interleaved code_review or code_localization
    runs that don't include any of the requested family's sample ids, or
    that include them only as `completed=False`/trace-not-found stubs)
    are filtered out so they don't displace family-relevant runs out of
    the most-recent-K window. This makes the default `seeds_per_model`
    cap behave correctly on mixed-category run trees.
    """
    out: list[Path] = []
    for ts_dir in sorted(model_dir.iterdir()):
        if not ts_dir.is_dir():
            continue
        scores_path = ts_dir / "scores.json"
        if not scores_path.is_file():
            continue
        try:
            scores = json.loads(scores_path.read_text())
        except Exception:
            continue
        for s in scores.get("samples", scores.get("results", [])):
            label = s.get("label") or s.get("name") or ""
            if not label.startswith("#"):
                continue
            try:
                sid = int(label[1:].split()[0])
            except ValueError:
                continue
            if sid in sample_ids_set and bool(s.get("completed")):
                out.append(ts_dir)
                break
    return out


def collect_runs(
    sample_ids: list[int],
    models: list[str] | None,
    seeds_per_model: int,
    exclude_incomplete: bool = False,
    superseded_before: dict[int, str] | None = None,
) -> dict[tuple[str, int, int], bool]:
    """Return mapping (model, seed_index, sample_id) -> pass (bool).

    For each model, we pick the most-recent `seeds_per_model` timestamped
    run directories that actually contain completed samples for the
    requested family. We deliberately do NOT fall back to older run dirs
    to backfill missing samples — older dirs often used earlier prompts
    and would mix vintages — but we DO skip run dirs that lack any
    family-relevant data (mixed-category run trees) before applying the
    seed cap.

    `exclude_incomplete=True` drops sample outcomes with `completed=False`
    (timeouts / trace-not-found) from the selected runs, so the
    per-(model, sample) denominator becomes "seeds that actually finished
    this sample" rather than "all seeds attempted".

    `superseded_before` maps `sid -> ts_prefix`. For each sid in the map,
    scored entries from run dirs whose name (a `2026-04-27T...` timestamp)
    sorts BEFORE `ts_prefix` are dropped. Used to retire pre-fix runs of
    samples that got a methodology bugfix without having to delete
    historical scores.json files.
    """
    sample_ids_set = set(sample_ids)
    out: dict[tuple[str, int, int], bool] = {}
    superseded_before = superseded_before or {}

    for model_dir in sorted(RUNS.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        if models and not any(m in model_name for m in models):
            continue

        # Family-relevant scored run dirs only. Most-recent K of those.
        scored_runs = _scored_runs_with_family_data(model_dir, sample_ids_set)
        chosen = scored_runs[-seeds_per_model:]

        for seed_idx, ts_dir in enumerate(chosen):
            try:
                scores = json.loads((ts_dir / "scores.json").read_text())
            except Exception:
                continue
            samples = scores.get("samples", scores.get("results", []))
            for s in samples:
                label = s.get("label") or s.get("name") or ""
                if not label.startswith("#"):
                    continue
                try:
                    sid = int(label[1:].split()[0])
                except ValueError:
                    continue
                if sid not in sample_ids_set:
                    continue
                if exclude_incomplete and not bool(s.get("completed")):
                    continue
                cutoff = superseded_before.get(sid)
                if cutoff is not None and ts_dir.name < cutoff:
                    continue
                out[(model_name, seed_idx, sid)] = bool(s.get("strict"))

    return out


def pass_vectors_by_sample(
    runs: dict[tuple[str, int, int], bool],
    sample_ids: list[int],
    drop_saturated_models: bool = True,
    saturation_scope_ids: list[int] | None = None,
) -> dict[int, list[int]]:
    """For each sample, return a flat list of 0/1 outcomes in a deterministic
    (model, seed) ordering. Used to compute sample-vs-sample Pearson
    correlation across the panel.

    Coverage handling: samples with zero trials are returned as empty
    vectors; samples with trials get a vector indexed over (model, seed)
    columns intersected across the *covered* samples (i.e. samples with
    n_trials > 0). This means an uncovered sample (e.g. just-redesigned,
    awaiting panel re-run) doesn't collapse the intersection to empty for
    every other sample. Pearson involving an empty vector returns None
    (the existing `pearson()` already handles that).

    Saturated-column drop: when `drop_saturated_models` is True, any model
    whose pass-rate across the saturation-scope sample ids is exactly 0.0
    or exactly 1.0 contributes zero variance to every sample's vector and
    is dropped from the Pearson computation entirely. By default the
    scope is the covered subset of `sample_ids` (family-level). Pass
    `saturation_scope_ids` to restrict the scope to a single tier --
    this avoids spurious r=1.0 flags caused by a model that's globally
    near-zero/near-one but exactly 0/N or N/N on the tier being
    correlated.
    """
    coverage = {sid: sum(1 for k in runs if k[2] == sid) for sid in sample_ids}
    covered_ids = [sid for sid in sample_ids if coverage[sid] > 0]

    # When `saturation_scope_ids` is supplied (tier-scoped mode), restrict the
    # column intersection to that scope too -- otherwise a model that's missing
    # one trial *outside* the tier (e.g. an easy timeout) gets dropped from
    # the medium correlation despite having full medium coverage. Family-wide
    # mode (scope=None) keeps the legacy behaviour.
    if saturation_scope_ids is not None:
        intersection_ids = [sid for sid in saturation_scope_ids if sid in covered_ids]
    else:
        intersection_ids = covered_ids

    all_cols = sorted({(m, s) for (m, s, _) in runs.keys()})
    common_cols = []
    for col in all_cols:
        if all((col[0], col[1], sid) in runs for sid in intersection_ids):
            common_cols.append(col)

    if drop_saturated_models and common_cols and intersection_ids:
        scope = saturation_scope_ids if saturation_scope_ids is not None else covered_ids
        scope = [sid for sid in scope if sid in covered_ids]
        if scope:
            per_model_pass: dict[str, list[int]] = {}
            for (m, s) in common_cols:
                for sid in scope:
                    per_model_pass.setdefault(m, []).append(int(runs[(m, s, sid)]))
            saturated = {
                m for m, vs in per_model_pass.items()
                if vs and (sum(vs) == 0 or sum(vs) == len(vs))
            }
            common_cols = [(m, s) for (m, s) in common_cols if m not in saturated]

    # Only sids in the (possibly tier-scoped) intersection are guaranteed to
    # have all `common_cols` trials present in `runs`. Out-of-scope sids are
    # returned as empty vectors -- callers handle them via their own tier's
    # invocation.
    in_scope = set(intersection_ids)
    out: dict[int, list[int]] = {}
    for sid in sample_ids:
        if sid not in in_scope or not common_cols:
            out[sid] = []
            continue
        try:
            out[sid] = [int(runs[(m, s, sid)]) for (m, s) in common_cols]
        except KeyError:
            out[sid] = []
    return out


def pearson(xs: list[int], ys: list[int]) -> float | None:
    """Plain Pearson correlation; returns None when either vector has zero
    variance (standard denominator goes to 0)."""
    n = len(xs)
    if n != len(ys) or n == 0:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def correlation_matrix(
    vecs: dict[int, list[int]],
    sample_ids: list[int],
) -> dict[int, dict[int, float | None]]:
    out: dict[int, dict[int, float | None]] = {}
    for i in sample_ids:
        out[i] = {}
        for j in sample_ids:
            out[i][j] = pearson(vecs[i], vecs[j]) if i != j else 1.0
    return out


def clone_flags(
    matrix: dict[int, dict[int, float | None]],
    sample_ids: list[int],
    threshold: float = 0.85,
) -> list[tuple[int, int, float]]:
    flags: list[tuple[int, int, float]] = []
    for i in range(len(sample_ids)):
        for j in range(i + 1, len(sample_ids)):
            a, b = sample_ids[i], sample_ids[j]
            r = matrix[a][b]
            if r is not None and r >= threshold:
                flags.append((a, b, r))
    return flags


def collect_opencode_metrics(
    sample_ids: list[int],
    models: list[str] | None,
    seeds_per_model: int,
    manifest: dict[int, dict[str, Any]] | None = None,
) -> dict[tuple[str, int, int], dict[str, Any]]:
    """Walk the same most-recent K family-relevant runs as collect_runs and
    extract opencode-specific per-trial metrics from each scores.json plus
    each per-sample trace JSONL.

    Returns mapping (model_name, seed_idx, sample_id) -> {
        "min_calls": int | None,
        "tool_calls_recursive": int | None,
        "schema_valid": int,            # count of well-formed tool calls
        "schema_total": int,            # total tool calls in trace
        "skill_calls": int,             # how many `skill name=X` calls in the trace
        "skill_correct": bool | None,   # did the trace include the expected skill name?
                                        # None when manifest doesn't declare expected_skill_invocations.
    }.

    `efficiency_multiple = tool_calls_recursive / min_calls` and
    `schema_validity_rate = schema_valid / schema_total` are computed at
    aggregation time so callers can pick their own per-model / per-tier
    rollup. `None` slots and zero denominators are skipped at rollup time.

    When `manifest` is supplied (i.e. the family has a per-sample manifest
    declaring `expected_skill_invocations`), the per-trial dict also
    populates `skill_correct` so the panel can compute `skill_load_rate`
    and `skill_correct_load_rate` per model.
    """
    sample_ids_set = set(sample_ids)
    out: dict[tuple[str, int, int], dict[str, Any]] = {}

    # Lazy: only import the schema validators if we have any runs to score.
    _validators = None
    def _make_validators():
        nonlocal _validators
        if _validators is None:
            sys.path.insert(0, str(ROOT))
            from evaluators.tool.call_schema_valid import _validators as v_factory
            _validators = v_factory()
        return _validators

    for model_dir in sorted(RUNS.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        if models and not any(m in model_name for m in models):
            continue

        scored_runs = _scored_runs_with_family_data(model_dir, sample_ids_set)
        chosen = scored_runs[-seeds_per_model:]

        for seed_idx, ts_dir in enumerate(chosen):
            try:
                scores = json.loads((ts_dir / "scores.json").read_text())
            except Exception:
                continue
            sample_entries = scores.get("samples", scores.get("results", []))
            for s in sample_entries:
                label = s.get("label") or s.get("name") or ""
                if not label.startswith("#"):
                    continue
                try:
                    sid = int(label[1:].split()[0])
                except ValueError:
                    continue
                if sid not in sample_ids_set:
                    continue
                if not bool(s.get("completed")):
                    continue

                # Trace file: NNN_<name>.jsonl. Name extraction matches eval.py's label format.
                # label is "#51 edit_iter_slices_require_positive" -> name = "edit_iter_slices_require_positive".
                bits = label[1:].split(maxsplit=1)
                name = bits[1] if len(bits) > 1 else ""
                trace_path = ts_dir / f"{sid:03d}_{name}.jsonl"
                schema_valid = schema_total = 0
                skill_calls = 0
                skill_names_invoked: set[str] = set()
                if trace_path.is_file():
                    try:
                        validators = _make_validators()
                        for line in trace_path.read_text().splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if obj.get("type") != "tool_use":
                                continue
                            part = obj.get("part") or {}
                            state = part.get("state") or {}
                            tool_name = part.get("tool", "")
                            tool_input = state.get("input") or {}
                            schema_total += 1
                            v = validators.get(tool_name)
                            if v is None:
                                continue  # unknown tool name -> not valid
                            errs = list(v.iter_errors(tool_input))
                            if not errs:
                                schema_valid += 1
                            # Track skill-tool invocations for the family-
                            # specific skill_load_rate / correct_load_rate
                            # rollups (no-op for non-skill samples).
                            if tool_name == "skill":
                                skill_calls += 1
                                sn = tool_input.get("name")
                                if isinstance(sn, str):
                                    skill_names_invoked.add(sn)
                    except Exception:
                        pass

                # skill_correct: True iff the trace invoked any of the
                # manifest's expected `must_invoke` skill names. Only
                # computed when the manifest entry declares those.
                skill_correct: bool | None = None
                if manifest is not None:
                    entry = manifest.get(sid) or {}
                    expected = entry.get("expected_skill_invocations") or []
                    must = [e.get("skill_name") for e in expected if e.get("must_invoke")]
                    if must:
                        skill_correct = any(name in skill_names_invoked for name in must)

                out[(model_name, seed_idx, sid)] = {
                    "min_calls": s.get("min_calls"),
                    "tool_calls_recursive": s.get("tool_calls_recursive"),
                    "schema_valid": schema_valid,
                    "schema_total": schema_total,
                    "skill_calls": skill_calls,
                    "skill_correct": skill_correct,
                }
    return out


def per_model_opencode_summary(
    metrics: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Aggregate per-trial opencode metrics into per-model summaries.

    Returns mapping model -> {
        "efficiency_mean": float | None,        # mean of tool_calls_recursive / min_calls
        "efficiency_n": int,                    # number of trials contributing
        "schema_validity_rate": float | None,   # schema_valid_total / schema_total_total
        "schema_n_calls": int,                  # total tool calls observed
    }.
    """
    by_model: dict[str, dict[str, Any]] = {}
    for (m, _seed, _sid), d in metrics.items():
        s = by_model.setdefault(m, {
            "eff_sum": 0.0,
            "eff_n": 0,
            "sv_valid": 0,
            "sv_total": 0,
            "skill_load_n_loaded": 0,
            "skill_load_n_total": 0,
            "skill_correct_n": 0,
            "skill_correct_n_total": 0,
        })
        mc = d.get("min_calls")
        tcr = d.get("tool_calls_recursive")
        if mc and tcr is not None and mc > 0:
            s["eff_sum"] += tcr / mc
            s["eff_n"] += 1
        s["sv_valid"] += d.get("schema_valid", 0)
        s["sv_total"] += d.get("schema_total", 0)
        # skill-load rate: of trials where the family declared `must_invoke`
        # skill names, how many had at least one skill call?
        if d.get("skill_correct") is not None:
            s["skill_load_n_total"] += 1
            if d.get("skill_calls", 0) > 0:
                s["skill_load_n_loaded"] += 1
            s["skill_correct_n_total"] += 1
            if d.get("skill_correct"):
                s["skill_correct_n"] += 1

    out: dict[str, dict[str, Any]] = {}
    for m, s in by_model.items():
        eff_mean = s["eff_sum"] / s["eff_n"] if s["eff_n"] else None
        sv_rate = s["sv_valid"] / s["sv_total"] if s["sv_total"] else None
        sl_rate = (
            s["skill_load_n_loaded"] / s["skill_load_n_total"]
            if s["skill_load_n_total"] else None
        )
        sc_rate = (
            s["skill_correct_n"] / s["skill_correct_n_total"]
            if s["skill_correct_n_total"] else None
        )
        out[m] = {
            "efficiency_mean": round(eff_mean, 3) if eff_mean is not None else None,
            "efficiency_n": s["eff_n"],
            "schema_validity_rate": round(sv_rate, 4) if sv_rate is not None else None,
            "schema_n_calls": s["sv_total"],
            "skill_load_rate": round(sl_rate, 4) if sl_rate is not None else None,
            "skill_correct_load_rate": round(sc_rate, 4) if sc_rate is not None else None,
            "skill_n_trials": s["skill_load_n_total"],
        }
    return out


def per_model_tier_pass_rate(
    runs: dict[tuple[str, int, int], bool],
    manifest: dict[int, dict[str, Any]],
    tier_field: str = "difficulty",
) -> dict[str, dict[str, tuple[int, int]]]:
    """(model -> tier -> (num_passed, num_total)).

    `tier_field` is read from each sample's manifest entry. Defaults to
    "difficulty" (localization/editing); mutants pass tier_field="mutation_kind"
    to get per-restriction-kind aggregation.
    """
    out: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (model, _seed, sid), passed in runs.items():
        tier = manifest.get(sid, {}).get(tier_field, "unknown")
        out[model][tier][1] += 1
        if passed:
            out[model][tier][0] += 1
    return {m: {t: (v[0], v[1]) for t, v in d.items()} for m, d in out.items()}


def gradient_violations(
    tier_rates: dict[str, dict[str, tuple[int, int]]]
) -> list[tuple[str, str, str, float, float]]:
    """Return (model, higher_tier, lower_tier, higher_rate, lower_rate) for
    any case where the "easier" tier has a lower pass rate than the
    "harder" tier. The expected ordering is easy >= medium >= hard."""
    order = ["easy", "medium", "hard"]
    out = []
    for model, tiers in tier_rates.items():
        rates = {}
        for t, (p, n) in tiers.items():
            if n > 0:
                rates[t] = p / n
        for a, b in zip(order, order[1:]):
            if a in rates and b in rates and rates[a] < rates[b]:
                out.append((model, a, b, rates[a], rates[b]))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--family", choices=sorted(FAMILIES), default="localization",
                   help="which sample family to analyze (default: localization).")
    p.add_argument("--ids", default=None,
                   help="sample id spec, e.g. 21-50,35. Defaults to the "
                        "family's full id range.")
    p.add_argument("--models", nargs="*", help="substring match on run subdir name")
    p.add_argument("--seeds-per-model", type=int, default=3)
    p.add_argument("--threshold", type=float, default=0.85, help="Pearson threshold for clone flag")
    p.add_argument("--exclude-incomplete", action="store_true",
                   help="drop trials where scores.json reports completed=false "
                        "(timeouts / trace-not-found). Useful when slow local "
                        "models time out on most of the panel.")
    p.add_argument("--json", action="store_true", help="emit JSON to stdout")
    p.add_argument("--rescan", action="store_true",
                   help="re-run eval.py for any run dir lacking scores.json")
    args = p.parse_args()

    family_cfg = FAMILIES[args.family]
    ids_spec = args.ids if args.ids is not None else family_cfg["default_ids"]
    sample_ids = parse_id_spec(ids_spec)
    manifest = load_manifest(args.family)

    if args.rescan:
        # Drive eval.py against the whole v1 panel so every run dir gains a
        # scores.json. Heavy but convenient when starting from a cold set.
        print(f"re-scoring all {args.family} runs via eval.py ...", file=sys.stderr)
        subprocess.run(
            [sys.executable, str(ROOT / "eval.py"), "--version", "v1",
             "--category", family_cfg["category"], "--format", "text"],
            cwd=str(ROOT), check=False,
        )

    # Build a per-sid `superseded_before` map from the manifest. Used to
    # retire pre-methodology-fix scored entries (e.g. mutant #219/#220 had
    # a wrong-shape persona overlay before 2026-04-27T15:00; runs from
    # before that cutoff don't actually test the persona-file mechanism
    # and would dilute the rerun signal).
    superseded_before: dict[int, str] = {}
    for sid, entry in manifest.items():
        ts = entry.get("superseded_before_run_ts")
        if ts:
            superseded_before[sid] = ts

    runs = collect_runs(
        sample_ids, args.models, args.seeds_per_model,
        exclude_incomplete=args.exclude_incomplete,
        superseded_before=superseded_before,
    )
    tier_field = family_cfg.get("tier_field", "difficulty")
    tier_order = family_cfg.get("tier_order")
    tier_rates = per_model_tier_pass_rate(runs, manifest, tier_field=tier_field)
    # Skip gradient analysis for families without an ordered tier vocabulary
    # (mutants are grouped by mutation_kind, which has no natural order).
    grads = gradient_violations(tier_rates) if tier_order is not None else []

    # Opencode-flavored signal: efficiency multiple + schema validity rate.
    # Pure reporting; doesn't gate pass/fail.
    oc_metrics = collect_opencode_metrics(
        sample_ids, args.models, args.seeds_per_model, manifest=manifest,
    )
    oc_summary = per_model_opencode_summary(oc_metrics)

    # Per-tier correlation grouping. Pearson is computed *within* each tier
    # with a tier-scoped saturated-column drop -- this stops a model that's
    # 0/N or N/N on the tier (but non-saturated family-wide) from injecting
    # zero-variance columns that drive r to 1.0 on otherwise-distinct samples.
    by_tier: dict[str, list[int]] = defaultdict(list)
    for sid in sample_ids:
        tier = manifest.get(sid, {}).get(tier_field, "unknown")
        by_tier[tier].append(sid)

    # Build a stitched global matrix: per-tier blocks populated, cross-tier
    # cells left as None (they are never used downstream).
    matrix: dict[int, dict[int, float | None]] = {
        i: {j: (1.0 if i == j else None) for j in sample_ids} for i in sample_ids
    }
    vecs: dict[int, list[int]] = {sid: [] for sid in sample_ids}
    same_tier_clones: list[tuple[str, int, int, float]] = []
    for tier, ids in by_tier.items():
        tier_vecs = pass_vectors_by_sample(
            runs, sample_ids, saturation_scope_ids=ids,
        )
        tier_matrix = correlation_matrix(tier_vecs, ids)
        for sid in ids:
            vecs[sid] = tier_vecs[sid]
        for i in ids:
            for j in ids:
                matrix[i][j] = tier_matrix[i][j]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                r = tier_matrix[a][b]
                if r is not None and r >= args.threshold:
                    same_tier_clones.append((tier, a, b, r))

    clones = clone_flags(matrix, sample_ids, threshold=args.threshold)

    report = {
        "family": args.family,
        "sample_ids": sample_ids,
        "n_trials": len(runs),
        "n_models": len({m for (m, _, _) in runs}),
        "coverage_per_sample": {sid: sum(1 for k in runs if k[2] == sid) for sid in sample_ids},
        "matrix": {
            str(i): {str(j): (round(v, 4) if v is not None else None) for j, v in row.items()}
            for i, row in matrix.items()
        },
        "threshold": args.threshold,
        "all_clone_flags": [(a, b, round(r, 4)) for a, b, r in clones],
        "same_tier_clone_flags": [
            {"tier": t, "sample_a": a, "sample_b": b, "pearson": round(r, 4)}
            for t, a, b, r in same_tier_clones
        ],
        "per_model_tier_rates": {
            m: {t: {"passed": p, "total": n, "rate": (p / n) if n else None}
                 for t, (p, n) in d.items()}
            for m, d in tier_rates.items()
        },
        "gradient_violations": [
            {"model": m, "higher_tier": ht, "lower_tier": lt,
             "higher_rate": round(hr, 4), "lower_rate": round(lr, 4)}
            for m, ht, lt, hr, lr in grads
        ],
        "opencode_signal": oc_summary,
    }

    # Mutants-only: per-(parent, restriction_kind, mechanism) pass-rate delta.
    # Computed up-front so it appears in both --json and text reports.
    mvp_records: list[dict[str, Any]] = []
    per_mech_delta: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    parent_runs: dict[tuple[str, int, int], bool] = {}
    if args.family == "mutants":
        parent_ids = sorted({
            manifest[sid]["parent_id"]
            for sid in sample_ids
            if sid in manifest and "parent_id" in manifest[sid]
        })
        parent_runs = collect_runs(
            parent_ids, args.models, args.seeds_per_model, exclude_incomplete=True,
        ) if parent_ids else {}

        def _pms(rs: dict) -> dict[str, dict[int, tuple[int, int]]]:
            d: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
            for (m, _seed, sid), passed in rs.items():
                d[m][sid][1] += 1
                if passed:
                    d[m][sid][0] += 1
            return {m: {sid: (v[0], v[1]) for sid, v in dd.items()} for m, dd in d.items()}

        mutant_pms = _pms(runs)
        parent_pms = _pms(parent_runs)
        all_models = sorted(set(mutant_pms) | set(parent_pms))
        for sid in sample_ids:
            e = manifest.get(sid, {})
            pid = e.get("parent_id")
            kind = e.get("mutation_kind", "?")
            if kind.endswith("_system"):
                mech = "system"
            elif kind.startswith("agents_md_"):
                mech = "agents_md"
            elif kind.startswith("persona_main_"):
                mech = "persona"
            else:
                mech = "?"
            row = {
                "id": sid,
                "name": e.get("name", "?"),
                "parent_id": pid,
                "mutation_kind": kind,
                "mechanism": mech,
                "per_model": {},
            }
            for m in all_models:
                mp, mn = mutant_pms.get(m, {}).get(sid, (0, 0))
                pp, pn = parent_pms.get(m, {}).get(pid, (0, 0))
                mrate = (mp / mn) if mn else None
                prate = (pp / pn) if pn else None
                delta = (prate - mrate) if (mrate is not None and prate is not None) else None
                row["per_model"][m] = {
                    "mutant_pass": mp, "mutant_total": mn, "mutant_rate": mrate,
                    "parent_pass": pp, "parent_total": pn, "parent_rate": prate,
                    "delta": delta,
                }
                if delta is not None:
                    per_mech_delta[mech][m].append(delta)
            mvp_records.append(row)
        report["mutant_vs_parent"] = mvp_records
        report["per_mechanism_mean_delta"] = {
            mech: {
                m: (sum(vals) / len(vals)) if vals else None
                for m, vals in d.items()
            }
            for mech, d in per_mech_delta.items()
        }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    # Text report
    print(f"Family: {args.family} (manifest {family_cfg['manifest'].name}, "
          f"category {family_cfg['category']})")
    print(f"Analyzed {report['n_trials']} trials across {report['n_models']} models")
    print(f"Sample coverage (trials per sample):")
    for sid in sample_ids:
        n = report["coverage_per_sample"][sid]
        tier = manifest.get(sid, {}).get(tier_field, "?")
        # Truncate long tier labels (e.g. mutation_kind values) for the column.
        tier_disp = tier if len(str(tier)) <= 28 else str(tier)[:25] + "..."
        print(f"  #{sid:<3} [{tier_disp:<28}] {n} trial(s)")
    print()
    if tier_order is not None:
        print(f"Per-tier clone flags (Pearson >= {args.threshold}):")
    else:
        print(f"Per-{tier_field} clone flags (Pearson >= {args.threshold}):")
    if not same_tier_clones:
        print("  (none) ✓")
    else:
        for t, a, b, r in same_tier_clones:
            t_disp = t if len(str(t)) <= 30 else str(t)[:27] + "..."
            print(f"  [{t_disp}] #{a} vs #{b}: r={r:.3f}")
    print()
    if tier_order is not None:
        print("Per-model pass rate by tier (passed / completed-trials [rate]):")
        print(f"  {'model':48} " + " ".join(f"{t:>16}" for t in tier_order))
        for m in sorted(tier_rates.keys()):
            bits = []
            for t in tier_order:
                p, n = tier_rates[m].get(t, (0, 0))
                bits.append(f"{p}/{n} [{p/n:.2f}]" if n else "-")
            print(f"  {m[:48]:48} " + " ".join(f"{b:>16}" for b in bits))
    else:
        # No tier ordering -- emit a long-form per-(model, group) table.
        all_tiers = sorted({t for d in tier_rates.values() for t in d})
        print(f"Per-model pass rate by {tier_field} (passed / completed-trials [rate]):")
        print(f"  {'model':48} {tier_field:<32} {'pass-rate':>16}")
        for m in sorted(tier_rates.keys()):
            for t in all_tiers:
                p, n = tier_rates[m].get(t, (0, 0))
                rate_str = f"{p}/{n} [{p/n:.2f}]" if n else "-"
                t_disp = t if len(str(t)) <= 32 else str(t)[:29] + "..."
                print(f"  {m[:48]:48} {t_disp:<32} {rate_str:>16}")
    print()
    print("Difficulty-gradient monotonicity violations (easy < medium < hard pass-rate):")
    if tier_order is None:
        print(f"  (skipped: family has no tier ordering)")
    elif not grads:
        print("  (none) ✓")
    else:
        for m, ht, lt, hr, lr in grads:
            print(f"  {m}: {ht}={hr:.3f} < {lt}={lr:.3f}")
    if oc_summary:
        # Surface skill_load_rate / skill_correct_load_rate columns only when
        # at least one model has data (i.e. when the family declares
        # expected_skill_invocations -- skill family today; future families
        # could opt in by adding the same field).
        any_skill_data = any(
            s.get("skill_load_rate") is not None or s.get("skill_correct_load_rate") is not None
            for s in oc_summary.values()
        )
        print()
        print("Opencode-flavored signal (per-model means across the family):")
        if any_skill_data:
            print(f"  {'model':48} {'eff_mult':>10} {'schema_validity':>17} {'skill_load':>12} {'skill_correct':>14}")
        else:
            print(f"  {'model':48} {'eff_mult':>10} {'schema_validity':>17}")
        for m in sorted(oc_summary.keys()):
            s = oc_summary[m]
            eff = s.get("efficiency_mean")
            eff_str = f"{eff:>4.2f}x ({s['efficiency_n']})" if eff is not None else "-"
            sv = s.get("schema_validity_rate")
            sv_str = f"{sv*100:>5.1f}% ({s['schema_n_calls']})" if sv is not None else "-"
            if any_skill_data:
                sl = s.get("skill_load_rate")
                sc = s.get("skill_correct_load_rate")
                sl_str = f"{sl*100:>5.1f}% ({s['skill_n_trials']})" if sl is not None else "-"
                sc_str = f"{sc*100:>5.1f}% ({s['skill_n_trials']})" if sc is not None else "-"
                print(f"  {m[:48]:48} {eff_str:>10} {sv_str:>17} {sl_str:>12} {sc_str:>14}")
            else:
                print(f"  {m[:48]:48} {eff_str:>10} {sv_str:>17}")

    # Mutants-only text section (data already on `report` above).
    if args.family == "mutants":
        all_models = sorted({m for r in mvp_records for m in r["per_model"]})
        print()
        print("Per-mutant vs parent pass-rate (delta = parent - mutant, per model):")
        for row in mvp_records:
            kind_disp = row["mutation_kind"]
            kind_disp = kind_disp if len(kind_disp) <= 32 else kind_disp[:29] + "..."
            print(f"  #{row['id']} {row['name'][:42]:<42} kind={kind_disp:<32} "
                  f"mech={row['mechanism']:<10} parent=#{row['parent_id']}")
            for m in all_models:
                cell = row["per_model"].get(m, {})
                pr = cell.get("parent_rate")
                mr = cell.get("mutant_rate")
                d = cell.get("delta")
                pr_s = f"{cell['parent_pass']}/{cell['parent_total']}={pr:.2f}" if pr is not None else "-"
                mr_s = f"{cell['mutant_pass']}/{cell['mutant_total']}={mr:.2f}" if mr is not None else "-"
                d_s = f"{d:+.2f}" if d is not None else "-"
                m_short = m[-48:] if len(m) > 48 else m
                print(f"      {m_short[:48]:<48}  parent={pr_s:<14}  mutant={mr_s:<14}  delta={d_s}")

        print()
        print("Per-mechanism mean delta (parent_pass - mutant_pass), per model:")
        for mech in sorted(report.get("per_mechanism_mean_delta", {})):
            print(f"  mechanism={mech}")
            for m, mean in sorted(report["per_mechanism_mean_delta"][mech].items()):
                if mean is None:
                    continue
                # Also show n for this (mech, model) cell.
                n = sum(1 for r in mvp_records
                        if r["mechanism"] == mech
                        and r["per_model"].get(m, {}).get("delta") is not None)
                print(f"    {m[:48]:<48}  mean_delta={mean:+.3f}  (n={n})")

        comparison_pairs = [
            ("bash-only on parent #51", 212, 219),
            ("subagent-required on parent #54", 216, 220),
        ]
        print()
        print("Same-restriction / different-mechanism pairs (AGENTS.md vs persona file):")
        rows_by_id = {r["id"]: r for r in mvp_records}
        for label, a, b in comparison_pairs:
            print(f"  {label}: #{a} (AGENTS.md) vs #{b} (persona)")
            ra = rows_by_id.get(a, {}).get("per_model", {})
            rb = rows_by_id.get(b, {}).get("per_model", {})
            for m in all_models:
                ar = ra.get(m, {}).get("mutant_rate")
                br = rb.get(m, {}).get("mutant_rate")
                a_pass, a_total = (ra.get(m, {}).get("mutant_pass", 0),
                                   ra.get(m, {}).get("mutant_total", 0))
                b_pass, b_total = (rb.get(m, {}).get("mutant_pass", 0),
                                   rb.get(m, {}).get("mutant_total", 0))
                a_s = f"{a_pass}/{a_total}={ar:.2f}" if ar is not None else "-"
                b_s = f"{b_pass}/{b_total}={br:.2f}" if br is not None else "-"
                gap = (ar - br) if (ar is not None and br is not None) else None
                gap_s = f"{gap:+.2f}" if gap is not None else "-"
                print(f"    {m[:48]:<48}  AGENTS.md={a_s:<14}  persona={b_s:<14}  gap={gap_s}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
