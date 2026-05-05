#!/usr/bin/env python3
"""audit_skill: validate v1 SKILL family samples against synthesized known-correct
and known-wrong traces, end-to-end through eval.py.

For each sample in `data/v1_skill_criteria.json`, this script:

  Pass 1 -- positive control:
    Build a synthetic JSONL trace that represents a model that did the right
    thing: loaded the prescribed skill via the `skill` tool, executed the
    prescribed inner tool sequence, and produced the prescribed artifact.
    Drive the trace through eval.py. Every check in the manifest must PASS.

  Pass 2 -- negative controls:
    For each documented failure mode (no skill loaded, wrong skill loaded,
    skill loaded but body ignored, skill bypassed via direct read of SKILL.md),
    build a synthetic trace that should fail the manifest's checks. At least
    ONE check must fail per negative trace.

The script is intentionally narrow: it validates the SAMPLE (its checks
discriminate correctly) rather than any model. Failures here mean the manifest
needs to be tightened (add more discriminating checks) or loosened (remove
spurious checks).

Usage:
    python3 data/scripts/audit_skill.py
    python3 data/scripts/audit_skill.py --id 401
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common import PROJECTS, load as common_load  # noqa: E402
from eval import evaluate, load_evaluators  # noqa: E402

MANIFEST = ROOT / "data" / "scripts" / "json" / "v1_skill_criteria.json"
SAMPLES_JSONL = ROOT / "data" / "samples_v1.jsonl"
SKILLS_DIR = PROJECTS / "v1" / "skills"
PROJECTS_V1 = PROJECTS / "v1"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _load_jsonl_sample(sid: int) -> dict | None:
    if not SAMPLES_JSONL.is_file():
        return None
    for line in SAMPLES_JSONL.read_text().splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        if s.get("id") == sid:
            return s
    return None


# ---------------------------------------------------------------------------
# Synthetic trace fragments
# ---------------------------------------------------------------------------


def _step_start_event(idx: int) -> dict:
    return {
        "type": "step_start",
        "timestamp": idx,
        "part": {"type": "step-start"},
    }


def _tool_use_event(name: str, input_obj: dict, output: str = "ok",
                    *, ts: int, call_id: str) -> dict:
    return {
        "type": "tool_use",
        "timestamp": ts,
        "part": {
            "type": "tool",
            "tool": name,
            "callID": call_id,
            "state": {
                "status": "completed",
                "input": input_obj,
                "output": output,
                "time": {"start": ts - 1, "end": ts},
            },
        },
    }


def _build_skill_load_event(skill_name: str, *, ts: int, call_id: str) -> dict:
    """A `skill` tool call loading a named skill."""
    return _tool_use_event(
        "skill",
        {"name": skill_name},
        output=f"<skill name='{skill_name}'>(body returned)</skill>",
        ts=ts,
        call_id=call_id,
    )


def _text_event(text: str, *, ts: int) -> dict:
    """An assistant text/response event. text_contains evaluators read these."""
    return {
        "type": "text",
        "timestamp": ts,
        "part": {"type": "text", "text": text, "time": {"start": ts - 1, "end": ts}},
    }


def _task_event(*, subagent_type: str, prompt_text: str, output: str,
                ts: int, call_id: str, description: str = "explore") -> dict:
    """A `task` tool call dispatching to a subagent."""
    return _tool_use_event(
        "task",
        {"description": description, "prompt": prompt_text, "subagent_type": subagent_type},
        output=output, ts=ts, call_id=call_id,
    )


def _grep_event(*, pattern: str, output: str, ts: int, call_id: str,
                path: str | None = None) -> dict:
    inp: dict = {"pattern": pattern}
    if path:
        inp["path"] = path
    return _tool_use_event("grep", inp, output=output, ts=ts, call_id=call_id)


def _bash_event(*, command: str, output: str, ts: int, call_id: str,
                description: str = "skill recipe") -> dict:
    return _tool_use_event("bash", {"command": command, "description": description},
                            output=output, ts=ts, call_id=call_id)


def _write_trace(run_dir: Path, sample: dict, events: list[dict]) -> None:
    path = run_dir / f"{sample['id']:03d}_{sample['name']}.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")


# ---------------------------------------------------------------------------
# Synth factories
# ---------------------------------------------------------------------------
# Each factory returns (positive_synth, negative_synth, labels) -- the same
# triple the SYNTHESIZERS dict below maps to. Negative synths take a label
# argument and dispatch to the right disk-state + trace pair.
#
# Patterns covered:
#   - workflow:    skill load -> read target -> write artifact
#   - style:       skill load -> (optional read existing) -> write file with rule markers
#   - code-backed: skill load -> bash invocation of sibling script -> text response with marker
#   - discovery:   correct skill load -> do task (negative: load distractor instead)


def make_workflow_synth(
    *,
    skill_name: str,
    read_rel: str,
    artifact_rel: str,
    artifact_correct: str,
    artifact_wrong: str,
    distractor_skill: str = "api-style",
):
    """Workflow sample: skill prescribes (read target file) -> (write artifact).

    Negatives:
      - no_skill_load        : reads/writes happen but `skill` tool never invoked
      - wrong_skill_name     : loads `distractor_skill` instead of `skill_name`
      - artifact_format_wrong: skill loaded; artifact written with wrong content
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        target = proj / read_rel
        artifact = proj / artifact_rel
        target_text = target.read_text() if target.is_file() else ""
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        events = [
            _step_start_event(1),
            _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
            _tool_use_event("read", {"filePath": str(target)},
                            output=f"<content>{target_text[:200]}</content>",
                            ts=3, call_id="t_read"),
            _step_start_event(4),
            _tool_use_event("write",
                            {"filePath": str(artifact), "content": artifact_correct},
                            output="wrote", ts=5, call_id="t_write"),
        ]
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        target = proj / read_rel
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if label == "no_skill_load":
            artifact.write_text(artifact_correct)
            events = [
                _step_start_event(1),
                _tool_use_event("read", {"filePath": str(target)}, ts=2, call_id="r1"),
                _tool_use_event("write",
                                {"filePath": str(artifact), "content": artifact_correct},
                                ts=3, call_id="w1"),
            ]
        elif label == "wrong_skill_name":
            artifact.write_text(artifact_correct)
            events = [
                _step_start_event(1),
                _build_skill_load_event(distractor_skill, ts=2, call_id="t_skill"),
                _tool_use_event("read", {"filePath": str(target)}, ts=3, call_id="r1"),
                _tool_use_event("write",
                                {"filePath": str(artifact), "content": artifact_correct},
                                ts=4, call_id="w1"),
            ]
        elif label == "artifact_format_wrong":
            artifact.write_text(artifact_wrong)
            events = [
                _step_start_event(1),
                _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
                _tool_use_event("read", {"filePath": str(target)}, ts=3, call_id="r1"),
                _tool_use_event("write",
                                {"filePath": str(artifact), "content": artifact_wrong},
                                ts=4, call_id="w1"),
            ]
        else:
            raise ValueError(label)
        _write_trace(run_dir, sample, events)

    return positive, negative, ["no_skill_load", "wrong_skill_name", "artifact_format_wrong"]


def make_style_synth(
    *,
    skill_name: str,
    write_rel: str,
    content_correct: str,
    content_violating: str,
    distractor_skill: str = "review-flow",
):
    """Style-rules sample: skill prescribes a content shape; user writes a fresh file.

    Negatives:
      - no_skill_load          : write happens without loading the skill
      - wrong_skill_name       : loads distractor; writes correct content (skill-name check fails)
      - file_violates_style    : skill loaded; written file lacks the prescribed markers
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        target = proj / write_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content_correct)
        events = [
            _step_start_event(1),
            _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
            _tool_use_event("write",
                            {"filePath": str(target), "content": content_correct},
                            output="wrote", ts=3, call_id="t_write"),
        ]
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        target = proj / write_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if label == "no_skill_load":
            target.write_text(content_correct)
            events = [
                _step_start_event(1),
                _tool_use_event("write",
                                {"filePath": str(target), "content": content_correct},
                                ts=2, call_id="w1"),
            ]
        elif label == "wrong_skill_name":
            target.write_text(content_correct)
            events = [
                _step_start_event(1),
                _build_skill_load_event(distractor_skill, ts=2, call_id="t_skill"),
                _tool_use_event("write",
                                {"filePath": str(target), "content": content_correct},
                                ts=3, call_id="w1"),
            ]
        elif label == "file_violates_style":
            target.write_text(content_violating)
            events = [
                _step_start_event(1),
                _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
                _tool_use_event("write",
                                {"filePath": str(target), "content": content_violating},
                                ts=3, call_id="w1"),
            ]
        else:
            raise ValueError(label)
        _write_trace(run_dir, sample, events)

    return positive, negative, ["no_skill_load", "wrong_skill_name", "file_violates_style"]


def make_codebacked_synth(
    *,
    skill_name: str,
    script_rel: str,
    bash_command_template: str,           # e.g. "python {proj}/scripts/checksum.py {arg}"
    bash_arg: str,                        # the argument substituted into the template
    response_marker: str,                 # the substring expected in the assistant's response
    response_text_correct: str,           # the assistant's full response in the positive case
    response_text_wrong: str,             # response that lacks `response_marker`
    distractor_skill: str = "api-style",
):
    """Code-backed sample: skill ships a sibling script; model loads skill, runs script, reports output.

    Negatives:
      - no_skill_load           : model runs the script via bash without loading skill
      - wrong_skill_name        : loads distractor; runs script; reports output
      - script_not_run          : skill loaded; bash never invoked; response hallucinated
      - output_not_in_response  : skill loaded; bash invoked; response lacks the marker
    """
    def _bash_event(proj: Path, *, ts: int, call_id: str, output: str) -> dict:
        cmd = bash_command_template.format(proj=str(proj), arg=bash_arg)
        return _tool_use_event(
            "bash",
            {"command": cmd, "description": f"run {skill_name} script"},
            output=output, ts=ts, call_id=call_id,
        )

    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        events = [
            _step_start_event(1),
            _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
            _bash_event(proj, ts=3, call_id="t_bash", output=response_marker),
            _step_start_event(4),
            _text_event(response_text_correct, ts=5),
        ]
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        if label == "no_skill_load":
            events = [
                _step_start_event(1),
                _bash_event(proj, ts=2, call_id="b1", output=response_marker),
                _text_event(response_text_correct, ts=3),
            ]
        elif label == "wrong_skill_name":
            events = [
                _step_start_event(1),
                _build_skill_load_event(distractor_skill, ts=2, call_id="t_skill"),
                _bash_event(proj, ts=3, call_id="b1", output=response_marker),
                _text_event(response_text_correct, ts=4),
            ]
        elif label == "script_not_run":
            events = [
                _step_start_event(1),
                _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
                _text_event(response_text_correct, ts=3),  # response has marker but no bash
            ]
        elif label == "output_not_in_response":
            events = [
                _step_start_event(1),
                _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
                _bash_event(proj, ts=3, call_id="b1", output=response_marker),
                _text_event(response_text_wrong, ts=4),
            ]
        else:
            raise ValueError(label)
        _write_trace(run_dir, sample, events)

    return positive, negative, [
        "no_skill_load", "wrong_skill_name", "script_not_run", "output_not_in_response",
    ]


def make_no_match_synth(
    *,
    distractor_skills: list[str],
    read_rel: str,
    artifact_rel: str,
    artifact_correct: str,
):
    """Discovery sample where NONE of the installed skills matches the user task.

    The model should solve it WITHOUT loading any skill (since none apply)
    and produce the prescribed artifact through normal read+write tools.

    Negatives:
      - loaded_irrelevant_skill : model loaded one of the distractors anyway
      - missing_artifact        : model didn't produce the artifact
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        target = proj / read_rel
        artifact = proj / artifact_rel
        target_text = target.read_text() if target.is_file() else ""
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        events = [
            _step_start_event(1),
            _tool_use_event("read", {"filePath": str(target)},
                            output=f"<content>{target_text[:200]}</content>",
                            ts=2, call_id="t_read"),
            _tool_use_event("write",
                            {"filePath": str(artifact), "content": artifact_correct},
                            ts=3, call_id="t_write"),
        ]
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        target = proj / read_rel
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if label == "loaded_irrelevant_skill":
            artifact.write_text(artifact_correct)
            events = [
                _step_start_event(1),
                _build_skill_load_event(distractor_skills[0], ts=2, call_id="t_skill"),
                _tool_use_event("read", {"filePath": str(target)}, ts=3, call_id="r1"),
                _tool_use_event("write",
                                {"filePath": str(artifact), "content": artifact_correct},
                                ts=4, call_id="w1"),
            ]
        elif label == "missing_artifact":
            # Don't write the artifact (and ensure it's not on disk from a prior case).
            if artifact.exists():
                artifact.unlink()
            events = [
                _step_start_event(1),
                _tool_use_event("read", {"filePath": str(target)}, ts=2, call_id="r1"),
            ]
        else:
            raise ValueError(label)
        _write_trace(run_dir, sample, events)

    return positive, negative, ["loaded_irrelevant_skill", "missing_artifact"]


def make_discovery_synth(
    *,
    correct_skill: str,
    distractor_skills: list[str],
    read_rel: str,
    artifact_rel: str,
    artifact_correct: str,
):
    """Discovery sample: multiple skills installed; only one matches the user task.

    Negatives:
      - no_skill_load     : no skill called at all
      - wrong_skill_name  : loads the first distractor skill (not the correct one)
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        target = proj / read_rel
        artifact = proj / artifact_rel
        target_text = target.read_text() if target.is_file() else ""
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        events = [
            _step_start_event(1),
            _build_skill_load_event(correct_skill, ts=2, call_id="t_skill"),
            _tool_use_event("read", {"filePath": str(target)},
                            output=f"<content>{target_text[:200]}</content>",
                            ts=3, call_id="t_read"),
            _tool_use_event("write",
                            {"filePath": str(artifact), "content": artifact_correct},
                            ts=4, call_id="t_write"),
        ]
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        target = proj / read_rel
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        if label == "no_skill_load":
            events = [
                _step_start_event(1),
                _tool_use_event("read", {"filePath": str(target)}, ts=2, call_id="r1"),
                _tool_use_event("write",
                                {"filePath": str(artifact), "content": artifact_correct},
                                ts=3, call_id="w1"),
            ]
        elif label == "wrong_skill_name":
            wrong = distractor_skills[0]
            events = [
                _step_start_event(1),
                _build_skill_load_event(wrong, ts=2, call_id="t_skill"),
                _tool_use_event("read", {"filePath": str(target)}, ts=3, call_id="r1"),
                _tool_use_event("write",
                                {"filePath": str(artifact), "content": artifact_correct},
                                ts=4, call_id="w1"),
            ]
        else:
            raise ValueError(label)
        _write_trace(run_dir, sample, events)

    return positive, negative, ["no_skill_load", "wrong_skill_name"]


# ---------------------------------------------------------------------------
# Per-sample trace synthesizers
# ---------------------------------------------------------------------------
# Each sample needs (a) a positive trace and (b) a list of negative traces.


def _proj_dir(run_dir: Path, sample: dict) -> Path:
    return run_dir / "projects" / f"{sample['id']:03d}"


def _materialize_workspace(run_dir: Path, sample: dict) -> None:
    """Copy the per-sample's parent repo + skill overlay into run_dir/projects/<sid>."""
    repos = json.loads((ROOT / "data" / "v1_repos.json").read_text())
    repo_meta = repos.get(sample["repo"])
    if not repo_meta:
        raise RuntimeError(f"unknown repo {sample['repo']}")
    src = ROOT / repo_meta["submodule_path"]
    dst = _proj_dir(run_dir, sample)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)
    overlay_src = SKILLS_DIR / f"{sample['id']:03d}"
    if overlay_src.is_dir():
        for item in overlay_src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(overlay_src)
                d2 = dst / rel
                d2.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, d2)


# SYNTHESIZERS dict: sid -> (positive_synth, negative_synth, [labels])
# Each entry uses one of the make_*_synth factories above so the per-sample
# audit logic stays declarative.

SYNTHESIZERS: dict[int, tuple] = {}

# -------------------- Tier A: workflow (#401-#403) -------------------------

SYNTHESIZERS[401] = make_workflow_synth(
    skill_name="review-flow",
    read_rel="src/requests/utils.py",
    artifact_rel="review.md",
    artifact_correct="# Review: utils.py\n## TODO Count: 0\n## Issues\nNo outstanding TODOs found.\n",
    artifact_wrong="Reviewed the file. No issues.\n",
    distractor_skill="api-style",
)

SYNTHESIZERS[402] = make_workflow_synth(
    skill_name="audit-flow",
    read_rel="train.py",
    artifact_rel="audit.md",
    artifact_correct="# Audit: train.py\n## Optimizer\nEMBEDDING_LR: 0.6\nWEIGHT_DECAY: 0.2\n## Tokenizer\nVOCAB_SIZE: 8192\n",
    artifact_wrong="The training script defines an optimizer.\n",
    distractor_skill="review-flow",
)

SYNTHESIZERS[403] = make_workflow_synth(
    skill_name="summary-flow",
    read_rel="httpx/_utils.py",
    artifact_rel="summary.md",
    artifact_correct="# Summary: _utils.py\n## Function Count: 9\n",
    artifact_wrong="The file is a utility module.\n",
    distractor_skill="api-style",
)

# -------------------- Tier A: style (#404-#406) ----------------------------

SYNTHESIZERS[404] = make_style_synth(
    skill_name="naming-convention",
    write_rel="helpers.py",
    content_correct=(
        "# AZ_HELPER\n"
        "def _az_compute_step_count(epochs, batches):\n"
        "    return epochs * batches\n"
    ),
    content_violating=(
        "def compute_step_count(epochs, batches):\n"
        "    return epochs * batches\n"
    ),
    distractor_skill="audit-flow",
)

SYNTHESIZERS[405] = make_style_synth(
    skill_name="api-style",
    write_rel="src/requests/handlers.py",
    content_correct=(
        "# API_HANDLER\n"
        "def handle_register(payload):\n"
        '    return (True, {"ok": True, "data": payload})\n'
    ),
    content_violating=(
        "def register(payload):\n"
        "    return payload\n"
    ),
    distractor_skill="review-flow",
)

SYNTHESIZERS[406] = make_style_synth(
    skill_name="encoding-convention",
    write_rel="httpx/_url_conv.py",
    content_correct=(
        "# ENCODING: utf-8 strict\n"
        "def bytes_url_to_str(value):\n"
        "    return value.decode('utf-8', errors='strict')\n"
    ),
    content_violating=(
        "def bytes_url_to_str(value):\n"
        "    return value.decode()\n"
    ),
    distractor_skill="summary-flow",
)

# -------------------- Tier A: code-backed (#407-#409) ----------------------

SYNTHESIZERS[407] = make_codebacked_synth(
    skill_name="validate-train",
    script_rel=".opencode/skills/validate-train/scripts/validate.py",
    bash_command_template="python {proj}/.opencode/skills/validate-train/scripts/validate.py",
    bash_arg="",
    response_marker="VALID_a8c9f1e2",
    response_text_correct="The validation script printed VALID_a8c9f1e2 on stdout.",
    response_text_wrong="The validation completed successfully.",
    distractor_skill="audit-flow",
)

SYNTHESIZERS[408] = make_codebacked_synth(
    skill_name="compute-checksum",
    script_rel=".opencode/skills/compute-checksum/scripts/checksum.py",
    bash_command_template="python {proj}/.opencode/skills/compute-checksum/scripts/checksum.py {arg}",
    bash_arg="src/requests/utils.py",
    response_marker="f67cc0",
    response_text_correct="The sha256 checksum starts with f67cc0.",
    response_text_wrong="The checksum was computed.",
    distractor_skill="review-flow",
)

SYNTHESIZERS[409] = make_codebacked_synth(
    skill_name="count-imports",
    script_rel=".opencode/skills/count-imports/scripts/count_imports.py",
    bash_command_template="python {proj}/.opencode/skills/count-imports/scripts/count_imports.py {arg}",
    bash_arg="httpx/_utils.py",
    response_marker="import_count=7",
    response_text_correct="The script reported import_count=7 for the file.",
    response_text_wrong="There were several imports.",
    distractor_skill="summary-flow",
)

# -------------------- Tier B: discovery (#410-#414) ------------------------

SYNTHESIZERS[410] = make_discovery_synth(
    correct_skill="review-flow",
    distractor_skills=["dependency-audit"],
    read_rel="src/requests/sessions.py",
    artifact_rel="review.md",
    artifact_correct="# Review: sessions.py\n## TODO Count: 0\n## Issues\nNone.\n",
)

SYNTHESIZERS[411] = make_discovery_synth(
    correct_skill="review-flow",
    distractor_skills=["dependency-audit", "validate-train"],
    read_rel="src/requests/auth.py",
    artifact_rel="review.md",
    artifact_correct="# Review: auth.py\n## TODO Count: 0\n## Issues\nNone.\n",
)

SYNTHESIZERS[412] = make_discovery_synth(
    correct_skill="xyz-001",
    distractor_skills=["abc-002", "def-003", "ghi-004", "jkl-005"],
    read_rel="src/requests/cookies.py",
    artifact_rel="review.md",
    artifact_correct="# Review: cookies.py\n## TODO Count: 0\n## Issues\nNone.\n",
)

SYNTHESIZERS[413] = make_discovery_synth(
    correct_skill="todo-review",
    # Closest distractor first -- the synth picks distractors[0] for the
    # wrong_skill_name negative case, so the audit deliberately tests the
    # most plausible mistake (loading the generic code-review skill instead).
    distractor_skills=["code-review", "style-check"],
    read_rel="src/requests/models.py",
    artifact_rel="review.md",
    artifact_correct="# Review: models.py\n## TODO Count: 0\n## Issues\nNone.\n",
)

SYNTHESIZERS[414] = make_no_match_synth(
    distractor_skills=["validate-train", "compute-checksum", "count-imports"],
    read_rel="src/requests/utils.py",
    artifact_rel="purpose.md",
    artifact_correct=(
        "This module provides internal utility helpers for the requests "
        "package: header parsing, URL normalization, cookie-jar manipulation, "
        "proxy resolution, and other small URL/HTTP plumbing primitives.\n"
    ),
)


# -------------------- Tier C: SKILL-vs-prompt delta (#415-#422) -------------
# Each Tier C sister mirrors a #301-#308 prescriptive parent. The recipe
# (graph shape + step sequence) lives in a SKILL.md instead of in the user
# prompt. The user prompt names only the high-level goal. The audit's
# positive trace exercises (skill_load -> prescribed_recipe -> artifact);
# negatives skip / mis-route the skill load.


def _tier_c_no_skill_negative(run_dir: Path, sample: dict, *,
                               artifact_rel: str, artifact_correct: str,
                               recipe_events_after_skill_load) -> None:
    """Run the prescribed recipe but DON'T load any skill.

    Common shape across all Tier C samples; the recipe events are
    sample-specific. recipe_events_after_skill_load is a callable that
    returns a list of events given (proj, base_ts).
    """
    proj = _proj_dir(run_dir, sample)
    artifact = proj / artifact_rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(artifact_correct)
    events = [_step_start_event(1)] + recipe_events_after_skill_load(proj, base_ts=2)
    _write_trace(run_dir, sample, events)


def _tier_c_wrong_skill_negative(run_dir: Path, sample: dict, *,
                                   wrong_skill: str,
                                   artifact_rel: str, artifact_correct: str,
                                   recipe_events_after_skill_load) -> None:
    """Load the WRONG skill name, then run the recipe."""
    proj = _proj_dir(run_dir, sample)
    artifact = proj / artifact_rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(artifact_correct)
    events = [
        _step_start_event(1),
        _build_skill_load_event(wrong_skill, ts=2, call_id="t_skill"),
    ] + recipe_events_after_skill_load(proj, base_ts=3)
    _write_trace(run_dir, sample, events)


def _tier_c_artifact_wrong_negative(run_dir: Path, sample: dict, *,
                                      skill_name: str,
                                      artifact_rel: str, artifact_wrong: str,
                                      recipe_events_after_skill_load_with_artifact) -> None:
    """Load the right skill + recipe, but write a wrong-format artifact."""
    proj = _proj_dir(run_dir, sample)
    artifact = proj / artifact_rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(artifact_wrong)
    events = [
        _step_start_event(1),
        _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
    ] + recipe_events_after_skill_load_with_artifact(proj, base_ts=3, artifact_content=artifact_wrong)
    _write_trace(run_dir, sample, events)


def make_tier_c_recipe_synth(*, skill_name: str, artifact_rel: str,
                              artifact_correct: str, artifact_wrong: str,
                              recipe_events,
                              wrong_skill: str = "review-flow"):
    """Generic Tier C synthesizer.

    `recipe_events(proj, *, base_ts, artifact_content) -> list[event]`
    callable returns the events that come AFTER the skill_load (or in place
    of it for the no-skill negative). `artifact_content` lets the recipe
    embed the model's `write` content, so artifact_format_wrong negatives
    can substitute the broken content.
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        events = [
            _step_start_event(1),
            _build_skill_load_event(skill_name, ts=2, call_id="t_skill"),
        ] + recipe_events(proj, base_ts=3, artifact_content=artifact_correct)
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        if label == "no_skill_load":
            _tier_c_no_skill_negative(
                run_dir, sample,
                artifact_rel=artifact_rel,
                artifact_correct=artifact_correct,
                recipe_events_after_skill_load=lambda proj, base_ts: recipe_events(
                    proj, base_ts=base_ts, artifact_content=artifact_correct,
                ),
            )
        elif label == "wrong_skill_name":
            _tier_c_wrong_skill_negative(
                run_dir, sample, wrong_skill=wrong_skill,
                artifact_rel=artifact_rel,
                artifact_correct=artifact_correct,
                recipe_events_after_skill_load=lambda proj, base_ts: recipe_events(
                    proj, base_ts=base_ts, artifact_content=artifact_correct,
                ),
            )
        elif label == "artifact_format_wrong":
            _tier_c_artifact_wrong_negative(
                run_dir, sample, skill_name=skill_name,
                artifact_rel=artifact_rel, artifact_wrong=artifact_wrong,
                recipe_events_after_skill_load_with_artifact=lambda proj, base_ts, artifact_content: recipe_events(
                    proj, base_ts=base_ts, artifact_content=artifact_content,
                ),
            )
        else:
            raise ValueError(label)

    return positive, negative, ["no_skill_load", "wrong_skill_name", "artifact_format_wrong"]


# Recipe builders for each Tier C sample. Each takes (proj, *, base_ts,
# artifact_content) and returns the list of events AFTER the skill_load.

def _recipe_415(proj, *, base_ts, artifact_content):
    """Parallel 3-facet audit on autoresearch (sister of #301)."""
    artifact = proj / "report.md"
    return [
        _step_start_event(base_ts),
        _task_event(subagent_type="explore", description="optimizer constants",
                    prompt_text="read train.py and report optimizer constants",
                    output="EMBEDDING_LR=0.6, UNEMBEDDING_LR=0.004, MATRIX_LR=0.04, WEIGHT_DECAY=0.2",
                    ts=base_ts + 1, call_id="t1"),
        _task_event(subagent_type="explore", description="top-level classes",
                    prompt_text="read train.py and list top-level classes",
                    output="GPTConfig, GPT, MuonAdamW",
                    ts=base_ts + 1, call_id="t2"),
        _task_event(subagent_type="explore", description="tokenizer constants",
                    prompt_text="read prepare.py and report tokenizer constants",
                    output="MAX_SEQ_LEN=1024, VOCAB_SIZE=8192, BOS_TOKEN=0",
                    ts=base_ts + 1, call_id="t3"),
        _step_start_event(base_ts + 2),
        _tool_use_event("write",
                        {"filePath": str(artifact), "content": artifact_content},
                        ts=base_ts + 3, call_id="w1"),
    ]


def _recipe_416(proj, *, base_ts, artifact_content):
    """Parallel 2-module compare on requests (sister of #302)."""
    artifact = proj / "comparison.md"
    return [
        _step_start_event(base_ts),
        _task_event(subagent_type="explore", description="Session methods",
                    prompt_text="list Session class public methods in source order",
                    output="prepare_request, send, get, options, head, post, put, patch, delete, request, get_adapter, mount, close, merge_environment_settings, rebuild_proxies, rebuild_method, rebuild_auth, resolve_redirects, get_redirect_target, should_strip_auth",
                    ts=base_ts + 1, call_id="t1"),
        _task_event(subagent_type="explore", description="HTTPAdapter methods",
                    prompt_text="list HTTPAdapter class public methods in source order",
                    output="init_poolmanager, proxy_manager_for, cert_verify, build_response, get_connection, request_url, add_headers, proxy_headers, send, close",
                    ts=base_ts + 1, call_id="t2"),
        _step_start_event(base_ts + 2),
        _tool_use_event("write",
                        {"filePath": str(artifact), "content": artifact_content},
                        ts=base_ts + 3, call_id="w1"),
    ]


def _recipe_417(proj, *, base_ts, artifact_content):
    """Chain read -> grep -> write on autoresearch (sister of #303)."""
    artifact = proj / "occurrences.md"
    target = proj / "train.py"
    return [
        _tool_use_event("read", {"filePath": str(target)}, ts=base_ts, call_id="r1"),
        _step_start_event(base_ts + 1),
        _grep_event(pattern="WEIGHT_DECAY", path=str(proj),
                    output="train.py:443\ntrain.py:505\ntrain.py:532",
                    ts=base_ts + 2, call_id="g1"),
        _step_start_event(base_ts + 3),
        _tool_use_event("write",
                        {"filePath": str(artifact), "content": artifact_content},
                        ts=base_ts + 4, call_id="w1"),
    ]


def _recipe_418(proj, *, base_ts, artifact_content):
    """Chain extract -> 8 greps -> report on requests (sister of #304)."""
    artifact = proj / "coverage.md"
    target = proj / "src" / "requests" / "api.py"
    events = [
        _tool_use_event("read", {"filePath": str(target)}, ts=base_ts, call_id="r1"),
    ]
    for i, name in enumerate(["request", "get", "options", "head", "post", "put", "patch", "delete"]):
        events.append(_step_start_event(base_ts + 1 + i))
        events.append(_grep_event(
            pattern=name, path=str(proj / "src" / "requests" / "sessions.py"),
            output=f"sessions.py:120: {name} call",
            ts=base_ts + 2 + i, call_id=f"g{i+1}",
        ))
    events.append(_step_start_event(base_ts + 10))
    events.append(_tool_use_event("write",
                                   {"filePath": str(artifact), "content": artifact_content},
                                   ts=base_ts + 11, call_id="w1"))
    return events


def _recipe_419(proj, *, base_ts, artifact_content):
    """DAG 2-input 1-output on autoresearch (sister of #305)."""
    artifact = proj / "combined.py"
    return [
        _step_start_event(base_ts),
        _task_event(subagent_type="explore", description="EMBEDDING_LR",
                    prompt_text="read train.py and report EMBEDDING_LR",
                    output="EMBEDDING_LR = 0.6", ts=base_ts + 1, call_id="t1"),
        _task_event(subagent_type="explore", description="VOCAB_SIZE",
                    prompt_text="read prepare.py and report VOCAB_SIZE",
                    output="VOCAB_SIZE = 8192", ts=base_ts + 1, call_id="t2"),
        _step_start_event(base_ts + 2),
        _tool_use_event("write",
                        {"filePath": str(artifact), "content": artifact_content},
                        ts=base_ts + 3, call_id="w1"),
    ]


def _recipe_420(proj, *, base_ts, artifact_content):
    """DAG response-attrs overlap on requests (sister of #306)."""
    artifact = proj / "attr_overlap.md"
    return [
        _step_start_event(base_ts),
        _task_event(subagent_type="explore", description="Response init attrs",
                    prompt_text="list Response.__init__ self assignments",
                    output="_content, _content_consumed, status_code, headers, raw, url, encoding, history, reason, cookies, elapsed, request",
                    ts=base_ts + 1, call_id="t1"),
        _task_event(subagent_type="explore", description="build_response attrs",
                    prompt_text="list build_response response.X assignments",
                    output="status_code, headers, encoding, raw, reason, url, request, connection",
                    ts=base_ts + 1, call_id="t2"),
        _step_start_event(base_ts + 2),
        _tool_use_event("write",
                        {"filePath": str(artifact), "content": artifact_content},
                        ts=base_ts + 3, call_id="w1"),
    ]


def _recipe_421(proj, *, base_ts, artifact_content):
    """Iter 4 bash grep -c on requests (sister of #307)."""
    artifact = proj / "def_count.md"
    files = [("adapters.py", 20), ("auth.py", 19), ("hooks.py", 2), ("sessions.py", 28)]
    events = []
    for i, (fname, n) in enumerate(files):
        events.append(_step_start_event(base_ts + i))
        events.append(_bash_event(
            command=f"grep -c 'def ' src/requests/{fname}",
            description=f"count def in {fname}",
            output=str(n), ts=base_ts + i + 1, call_id=f"b{i+1}",
        ))
    events.append(_step_start_event(base_ts + len(files)))
    events.append(_tool_use_event("write",
                                   {"filePath": str(artifact), "content": artifact_content},
                                   ts=base_ts + len(files) + 1, call_id="w1"))
    return events


def _recipe_422(proj, *, base_ts, artifact_content):
    """Iter 3 separate greps (sister of #308)."""
    artifact = proj / "caller_table.md"
    helpers = [("merge_setting", 9), ("to_key_val_list", 3), ("iter_slices", 0)]
    events = []
    for i, (helper, n) in enumerate(helpers):
        events.append(_step_start_event(base_ts + i))
        events.append(_grep_event(
            pattern=helper, path=str(proj / "src" / "requests" / "sessions.py"),
            output=f"matches: {n}", ts=base_ts + i + 1, call_id=f"g{i+1}",
        ))
    events.append(_step_start_event(base_ts + len(helpers)))
    events.append(_tool_use_event("write",
                                   {"filePath": str(artifact), "content": artifact_content},
                                   ts=base_ts + len(helpers) + 1, call_id="w1"))
    return events


SYNTHESIZERS[415] = make_tier_c_recipe_synth(
    skill_name="parallel-3-facet-audit",
    artifact_rel="report.md",
    artifact_correct=(
        "# Audit\n\n## Optimizer\nEMBEDDING_LR: 0.6\nUNEMBEDDING_LR: 0.004\n"
        "MATRIX_LR: 0.04\nWEIGHT_DECAY: 0.2\n\n## Classes\nGPTConfig\nGPT\nMuonAdamW\n\n"
        "## Tokenizer\nVOCAB_SIZE: 8192\n"
    ),
    artifact_wrong="An audit was performed.\n",
    recipe_events=_recipe_415,
)

SYNTHESIZERS[416] = make_tier_c_recipe_synth(
    skill_name="parallel-2-module-compare",
    artifact_rel="comparison.md",
    artifact_correct=(
        "## Session\nprepare_request\nmerge_environment_settings\nsend\n\n"
        "## HTTPAdapter\ninit_poolmanager\nbuild_response\nsend\n"
    ),
    artifact_wrong="Compared the two modules.\n",
    recipe_events=_recipe_416,
)

SYNTHESIZERS[417] = make_tier_c_recipe_synth(
    skill_name="chain-read-grep-edit",
    artifact_rel="occurrences.md",
    artifact_correct="train.py:443\ntrain.py:505\ntrain.py:532\n",
    artifact_wrong="No matches found.\n",
    recipe_events=_recipe_417,
)

SYNTHESIZERS[418] = make_tier_c_recipe_synth(
    skill_name="chain-extract-check-report",
    artifact_rel="coverage.md",
    artifact_correct=(
        "request: used\nget: used\noptions: used\nhead: used\n"
        "post: used\nput: used\npatch: used\ndelete: used\n"
    ),
    artifact_wrong="All functions covered.\n",
    recipe_events=_recipe_418,
)

SYNTHESIZERS[419] = make_tier_c_recipe_synth(
    skill_name="dag-two-inputs-one-output",
    artifact_rel="combined.py",
    artifact_correct="EMBEDDING_LR = 0.6\nVOCAB_SIZE = 8192\n",
    artifact_wrong="# combined values\nEMBEDDING_LR = 0.5\n",
    recipe_events=_recipe_419,
)

SYNTHESIZERS[420] = make_tier_c_recipe_synth(
    skill_name="dag-response-attrs",
    artifact_rel="attr_overlap.md",
    artifact_correct=(
        "## __init__ attrs\n_content\nencoding\nstatus_code\nurl\n\n"
        "## build_response attrs\nencoding\nstatus_code\nurl\n\n"
        "## overlap\nencoding\nstatus_code\nurl\n"
    ),
    artifact_wrong="Attributes were compared.\n",
    recipe_events=_recipe_420,
)

SYNTHESIZERS[421] = make_tier_c_recipe_synth(
    skill_name="iter-def-count",
    artifact_rel="def_count.md",
    artifact_correct=(
        "src/requests/adapters.py: 20\nsrc/requests/auth.py: 19\n"
        "src/requests/hooks.py: 2\nsrc/requests/sessions.py: 28\n"
    ),
    artifact_wrong="Def counts computed.\n",
    recipe_events=_recipe_421,
)

SYNTHESIZERS[422] = make_tier_c_recipe_synth(
    skill_name="iter-helper-callers",
    artifact_rel="caller_table.md",
    artifact_correct="merge_setting: 9\nto_key_val_list: 3\niter_slices: 0\n",
    artifact_wrong="Caller counts computed.\n",
    recipe_events=_recipe_422,
)


# -------------------- Tier D: selectivity (#423-#426) ----------------------
# Tier D differs from Tier B in the negative-selectivity emphasis: distractors
# are deliberately PLAUSIBLY relevant (vocabulary overlap) and the audit
# verifies the model resisted loading them. Each Tier D sample's manifest
# carries no_tool_param_value_recursive checks for every must_not_invoke
# distractor.


def make_selectivity_synth(*,
                           correct_skill: str | None,   # None means "no skill should load"
                           distractor_skills: list[str],
                           read_rel: str | None,
                           artifact_rel: str,
                           artifact_correct: str,
                           artifact_wrong: str | None = None):
    """Selectivity synth.

    correct_skill: which skill SHOULD load (None = no skill should load).
    distractor_skills: skill names that should NOT load (negatives load distractor[0]).

    Negatives:
      - no_skill_load        (only meaningful when correct_skill is set)
      - loaded_distractor    (loads distractor_skills[0])
      - artifact_format_wrong (loaded right + wrote wrong content)
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        events = [_step_start_event(1)]
        ts = 2
        if correct_skill:
            events.append(_build_skill_load_event(correct_skill, ts=ts, call_id="t_skill"))
            ts += 1
        if read_rel:
            target = proj / read_rel
            events.append(_tool_use_event("read", {"filePath": str(target)},
                                          ts=ts, call_id="r1"))
            ts += 1
        events.append(_tool_use_event(
            "write", {"filePath": str(artifact), "content": artifact_correct},
            ts=ts, call_id="w1",
        ))
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if label == "no_skill_load" and correct_skill is not None:
            artifact.write_text(artifact_correct)
            ev: list[dict] = [_step_start_event(1)]
            if read_rel:
                ev.append(_tool_use_event("read", {"filePath": str(proj / read_rel)},
                                           ts=2, call_id="r1"))
            ev.append(_tool_use_event("write",
                                       {"filePath": str(artifact), "content": artifact_correct},
                                       ts=3, call_id="w1"))
            _write_trace(run_dir, sample, ev)
        elif label == "loaded_distractor":
            artifact.write_text(artifact_correct)
            ev = [
                _step_start_event(1),
                _build_skill_load_event(distractor_skills[0], ts=2, call_id="t_skill"),
            ]
            if read_rel:
                ev.append(_tool_use_event("read", {"filePath": str(proj / read_rel)},
                                           ts=3, call_id="r1"))
            ev.append(_tool_use_event("write",
                                       {"filePath": str(artifact), "content": artifact_correct},
                                       ts=4, call_id="w1"))
            _write_trace(run_dir, sample, ev)
        elif label == "artifact_format_wrong" and correct_skill is not None and artifact_wrong:
            artifact.write_text(artifact_wrong)
            ev = [
                _step_start_event(1),
                _build_skill_load_event(correct_skill, ts=2, call_id="t_skill"),
            ]
            if read_rel:
                ev.append(_tool_use_event("read", {"filePath": str(proj / read_rel)},
                                           ts=3, call_id="r1"))
            ev.append(_tool_use_event("write",
                                       {"filePath": str(artifact), "content": artifact_wrong},
                                       ts=4, call_id="w1"))
            _write_trace(run_dir, sample, ev)
        else:
            raise ValueError(label)

    labels = []
    if correct_skill is not None:
        labels.append("no_skill_load")
    labels.append("loaded_distractor")
    if correct_skill is not None and artifact_wrong is not None:
        labels.append("artifact_format_wrong")
    return positive, negative, labels


# Tier D sample registrations -----------------------------------------------

SYNTHESIZERS[423] = make_selectivity_synth(
    correct_skill="todo-review",
    distractor_skills=["python-code-review", "js-todo-review",
                       "style-check", "comment-review"],
    read_rel="src/requests/auth.py",
    artifact_rel="review.md",
    artifact_correct="# Review: auth.py\n## TODO Count: 0\n## Issues\nNone.\n",
    artifact_wrong="Reviewed auth.py.\n",
)

SYNTHESIZERS[424] = make_selectivity_synth(
    correct_skill=None,    # NO skill matches the task
    distractor_skills=["train-validator", "lint-runner", "security-scanner"],
    read_rel="src/requests/utils.py",
    artifact_rel="purpose.md",
    artifact_correct=(
        "This module provides internal utility helpers for the requests "
        "package: header parsing, URL normalization, cookie-jar manipulation, "
        "proxy resolution, and other small URL/HTTP plumbing primitives.\n"
    ),
)

SYNTHESIZERS[425] = make_selectivity_synth(
    correct_skill="python-review",
    distractor_skills=["javascript-review"],
    read_rel="src/requests/auth.py",
    artifact_rel="review.md",
    artifact_correct="# Review: auth.py\n## TODO Count: 0\n## Issues\nNone.\n",
    artifact_wrong="Reviewed auth.py.\n",
)

SYNTHESIZERS[426] = make_selectivity_synth(
    correct_skill="code-review",
    distractor_skills=["code-style-format", "code-coverage-report"],
    read_rel="src/requests/auth.py",
    artifact_rel="review.md",
    artifact_correct="# Review: auth.py\n## TODO Count: 0\n## Issues\nNone.\n",
    artifact_wrong="Reviewed auth.py.\n",
)


# -------------------- Tier E: composition (#427-#430) ----------------------
# Composition samples chain or parallel-load multiple skills. Each has
# expected_skill_invocations covering ALL must-load skills; manifest
# checks pin per-skill any_tool_param_value_recursive plus tool_before
# for sequential ordering where required.


def make_composition_synth(*,
                           skill_loads: list[str],          # in load-order
                           after_skill_events,              # callable: (proj, base_ts) -> list[event]
                           artifact_rel: str,
                           artifact_correct: str,
                           artifact_wrong: str,
                           one_skill_only_subset: list[str] | None = None):
    """Composition synth.

    skill_loads: ordered list of skill names the model must load (one per
                 turn for sequential, in same turn for parallel).
    after_skill_events: callable producing the recipe events (read/write/etc.)
    one_skill_only_subset: subset of skill_loads to use in the
                            'one_skill_only' negative (exercises the
                            'forgot to load skill B' failure mode).
    """
    def positive(run_dir, sample):
        proj = _proj_dir(run_dir, sample)
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(artifact_correct)
        events = [_step_start_event(1)]
        ts = 2
        for sk in skill_loads:
            events.append(_build_skill_load_event(sk, ts=ts, call_id=f"t_{sk}"))
            ts += 1
            events.append(_step_start_event(ts)); ts += 1
        events += after_skill_events(proj, base_ts=ts)
        _write_trace(run_dir, sample, events)

    def negative(run_dir, sample, label):
        proj = _proj_dir(run_dir, sample)
        artifact = proj / artifact_rel
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if label == "no_skill_load":
            artifact.write_text(artifact_correct)
            events = [_step_start_event(1)] + after_skill_events(proj, base_ts=2)
            _write_trace(run_dir, sample, events)
        elif label == "one_skill_only" and one_skill_only_subset:
            artifact.write_text(artifact_correct)
            events = [_step_start_event(1)]
            ts = 2
            for sk in one_skill_only_subset:
                events.append(_build_skill_load_event(sk, ts=ts, call_id=f"t_{sk}"))
                ts += 1
            events += after_skill_events(proj, base_ts=ts)
            _write_trace(run_dir, sample, events)
        elif label == "artifact_format_wrong":
            artifact.write_text(artifact_wrong)
            events = [_step_start_event(1)]
            ts = 2
            for sk in skill_loads:
                events.append(_build_skill_load_event(sk, ts=ts, call_id=f"t_{sk}"))
                ts += 1
            ev_after = after_skill_events(proj, base_ts=ts)
            # Replace any 'write' event's content with the wrong content.
            patched = []
            for e in ev_after:
                p = e.get("part") or {}
                if e.get("type") == "tool_use" and p.get("tool") == "write":
                    e2 = json.loads(json.dumps(e))
                    e2["part"]["state"]["input"]["content"] = artifact_wrong
                    patched.append(e2)
                else:
                    patched.append(e)
            events += patched
            _write_trace(run_dir, sample, events)
        else:
            raise ValueError(label)

    labels = ["no_skill_load"]
    if one_skill_only_subset:
        labels.append("one_skill_only")
    labels.append("artifact_format_wrong")
    return positive, negative, labels


# Per-sample after-skill recipe builders for Tier E.

def _comp_427_recipe(proj, *, base_ts):
    """Sequential: validate-train ran, output written, then review-flow runs review."""
    val_out = proj / "validation_output.md"
    review = proj / "review.md"
    return [
        _bash_event(
            command=f"python {proj}/.opencode/skills/validate-train/scripts/validate.py",
            description="run validate-train script",
            output="VALID_a8c9f1e2",
            ts=base_ts, call_id="b1",
        ),
        _tool_use_event("write",
                        {"filePath": str(val_out),
                         "content": "VALID_a8c9f1e2\n# TODO: investigate this token\n"},
                        ts=base_ts + 1, call_id="w1"),
        _step_start_event(base_ts + 2),
        _tool_use_event("read", {"filePath": str(val_out)},
                        ts=base_ts + 3, call_id="r1"),
        _tool_use_event("write", {"filePath": str(review), "content": (
            "# Review: validation_output.md\n"
            "## TODO Count: 1\n## Issues\n- TODO: investigate this token\n"
            "VALID_a8c9f1e2\n")},
                        ts=base_ts + 4, call_id="w2"),
    ]


def _comp_428_recipe(proj, *, base_ts):
    """Independent: audit-flow writes audit.md, naming-convention writes helpers.py."""
    audit_md = proj / "audit.md"
    helpers = proj / "helpers.py"
    return [
        _tool_use_event("read", {"filePath": str(proj / "train.py")},
                        ts=base_ts, call_id="r1"),
        _tool_use_event("write", {"filePath": str(audit_md), "content": (
            "# Audit: train.py\n## Optimizer\nEMBEDDING_LR: 0.6\n## Tokenizer\nVOCAB_SIZE: 8192\n")},
                        ts=base_ts + 1, call_id="w1"),
        _step_start_event(base_ts + 2),
        _tool_use_event("write", {"filePath": str(helpers), "content": (
            "# AZ_HELPER\ndef _az_compute_step_count(epochs, batches):\n    return epochs * batches\n")},
                        ts=base_ts + 3, call_id="w2"),
    ]


def _comp_429_recipe(proj, *, base_ts):
    """Prose-chained: super-review's body says to load review-flow next."""
    review = proj / "review.md"
    return [
        _tool_use_event("read", {"filePath": str(proj / "src/requests/auth.py")},
                        ts=base_ts, call_id="r1"),
        _tool_use_event("write", {"filePath": str(review), "content": (
            "# Review: auth.py\n## TODO Count: 0\n## Issues\nNo outstanding TODOs found.\n")},
                        ts=base_ts + 1, call_id="w1"),
    ]


def _comp_430_recipe(proj, *, base_ts):
    """Three-skill: validate + count-imports + review."""
    report = proj / "comprehensive_report.md"
    return [
        _bash_event(
            command=f"python {proj}/.opencode/skills/validate-train/scripts/validate.py",
            description="validate", output="VALID_a8c9f1e2",
            ts=base_ts, call_id="b1"),
        _bash_event(
            command=f"python {proj}/.opencode/skills/count-imports/scripts/count_imports.py train.py",
            description="count imports", output="import_count=12",
            ts=base_ts + 1, call_id="b2"),
        _step_start_event(base_ts + 2),
        _tool_use_event("read", {"filePath": str(proj / "train.py")},
                        ts=base_ts + 3, call_id="r1"),
        _tool_use_event("write", {"filePath": str(report), "content": (
            "# Comprehensive Report\n## Validation\nVALID_a8c9f1e2\n"
            "## Imports\nimport_count=12\n## Review\n# Review: train.py\n"
            "## TODO Count: 0\n## Issues\nNone.\n")},
                        ts=base_ts + 4, call_id="w1"),
    ]


SYNTHESIZERS[427] = make_composition_synth(
    skill_loads=["validate-train", "review-flow"],
    after_skill_events=_comp_427_recipe,
    artifact_rel="review.md",
    artifact_correct=(
        "# Review: validation_output.md\n## TODO Count: 1\n"
        "## Issues\n- TODO: investigate this token\nVALID_a8c9f1e2\n"
    ),
    artifact_wrong="Reviewed.\n",
    one_skill_only_subset=["validate-train"],   # forgot to load review-flow
)

SYNTHESIZERS[428] = make_composition_synth(
    skill_loads=["audit-flow", "naming-convention"],
    after_skill_events=_comp_428_recipe,
    artifact_rel="helpers.py",
    artifact_correct=(
        "# AZ_HELPER\n"
        "def _az_compute_step_count(epochs, batches):\n"
        "    return epochs * batches\n"
    ),
    artifact_wrong="def compute(): pass\n",
    one_skill_only_subset=["audit-flow"],   # forgot to load naming-convention
)

SYNTHESIZERS[429] = make_composition_synth(
    skill_loads=["super-review"],   # super-review's prose says to also load review-flow
    after_skill_events=_comp_429_recipe,
    artifact_rel="review.md",
    artifact_correct=(
        "# Review: auth.py\n## TODO Count: 0\n"
        "## Issues\nNo outstanding TODOs found.\n"
    ),
    artifact_wrong="Reviewed.\n",
    one_skill_only_subset=None,   # no subset variant -- only one skill is "must-load"
)

SYNTHESIZERS[430] = make_composition_synth(
    skill_loads=["validate-train", "count-imports", "review-flow"],
    after_skill_events=_comp_430_recipe,
    artifact_rel="comprehensive_report.md",
    artifact_correct=(
        "# Comprehensive Report\n## Validation\nVALID_a8c9f1e2\n"
        "## Imports\nimport_count=12\n## Review\n# Review: train.py\n"
        "## TODO Count: 0\n## Issues\nNone.\n"
    ),
    artifact_wrong="Report generated.\n",
    one_skill_only_subset=["validate-train"],   # forgot to load count-imports + review-flow
)


def _clear_eval_caches() -> None:
    """Clear caches that would otherwise stale-cache trace data across cases.

    `evaluators._recursive._collect_recursive_tools` is `@lru_cache` keyed on the
    canonical trace path -- which we deliberately reuse for each negative case.
    Without clearing, the second+ call returns the first case's tool list."""
    try:
        from evaluators._recursive import _collect_recursive_tools as _crt
        _crt.cache_clear()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Audit driver
# ---------------------------------------------------------------------------


def audit_one(sample: dict) -> tuple[bool, list[str]]:
    """Run positive + negative passes for one sample. Return (overall_ok, error_messages)."""
    sid = sample["id"]
    if sid not in SYNTHESIZERS:
        return False, [f"#{sid}: no synthesizer registered for this sample id (add to SYNTHESIZERS)"]
    positive_synth, negative_synth, labels = SYNTHESIZERS[sid]

    jsonl_sample = _load_jsonl_sample(sid)
    if jsonl_sample is None:
        return False, [f"#{sid}: not in {SAMPLES_JSONL.relative_to(ROOT)}; run regen_skill.py first"]

    errs: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"audit_skill_{sid}_") as td:
        run_dir = Path(td)
        # ----- Positive ------------------------------------------------------
        _materialize_workspace(run_dir, jsonl_sample)
        positive_synth(run_dir, jsonl_sample)
        _clear_eval_caches()
        result = evaluate(jsonl_sample, run_dir)
        if result.failed:
            errs.append(f"#{sid}: positive trace had failed checks: {result.failed[:3]}")
        if not result.passed:
            errs.append(f"#{sid}: positive trace had no passed checks (suspicious)")

        # ----- Negatives -----------------------------------------------------
        for label in labels:
            _materialize_workspace(run_dir, jsonl_sample)
            negative_synth(run_dir, jsonl_sample, label)
            _clear_eval_caches()
            result = evaluate(jsonl_sample, run_dir)
            if not result.failed:
                errs.append(f"#{sid}: negative trace {label!r} unexpectedly passed all checks")

    return len(errs) == 0, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, default=None)
    args = ap.parse_args()

    load_evaluators()
    manifest = _load_manifest()
    samples = manifest.get("samples", [])
    if args.id is not None:
        samples = [s for s in samples if s.get("id") == args.id]

    print("=" * 60)
    print("Skill-family audit")
    print("=" * 60)
    failures = 0
    for s in samples:
        ok, errs = audit_one(s)
        if ok:
            print(f"  PASS #{s['id']} {s['name']}")
        else:
            print(f"  FAIL #{s['id']} {s['name']}")
            for e in errs:
                print(f"    - {e}")
            failures += 1
    print()
    print("=" * 60)
    if failures:
        print(f"RESULT: FAIL ({failures} sample(s) failed audit)")
        return 1
    print(f"RESULT: PASS (all {len(samples)} samples validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
