"""
Validate every tool call in a trace against opencode's canonical JSON Schemas.

Schemas come from `data/tool_schemas.json`, extracted by `scripts/extract_schemas.py`
(also reachable via `python eval.py --refresh-schemas`). Extra/missing/misspelled
parameters, wrong types, and calls to tools that aren't in opencode all fail the
check. This is therefore opt-in per sample: don't add it to samples that
intentionally exercise non-opencode tools (plugins, custom agents, etc.).

When `trace_path` is supplied, the check recurses by default: calls made inside
any `task` subagent are validated alongside the parent's calls. There's no
meaningful use case for accepting malformed calls from a subagent while holding
the parent to strict validation, so this is always the right behavior. The
`trace_path=None` fallback preserves the old strict semantics for the test
harness and any other in-process caller that doesn't have a trace file.
"""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from evaluators import register

SCHEMAS_PATH = Path(__file__).resolve().parents[2] / "data" / "tool_schemas.json"


@lru_cache(maxsize=1)
def _validators():
    if not SCHEMAS_PATH.exists():
        raise FileNotFoundError(
            f"{SCHEMAS_PATH} missing; run `python eval.py --refresh-schemas` "
            "or `python scripts/extract_schemas.py`"
        )
    data = json.loads(SCHEMAS_PATH.read_text())
    out = {}
    for tid, entry in data["tools"].items():
        schema = dict(entry["parameters"])
        if schema.get("type") == "object" and "additionalProperties" not in schema:
            schema["additionalProperties"] = False
        out[tid] = Draft202012Validator(schema)
    return out


@register("call_schema_valid")
def check(tools, texts, chk, trace_path=None):
    # Lazy imports so `evaluators._recursive` stays an optional dep of the
    # strict test-harness entry point.
    if trace_path is not None:
        from evaluators._recursive import (
            _collect_recursive_tools, _check_sentinels, _real_tools,
        )
        recursive_tools = _collect_recursive_tools(trace_path)
        sentinel = _check_sentinels(recursive_tools)
        if sentinel is not None:
            return sentinel
        tools = _real_tools(recursive_tools)

    validators = _validators()
    bad = []
    for call in tools:
        name = call["name"]
        v = validators.get(name)
        if v is None:
            bad.append(f"unknown tool {name!r}")
            continue
        for err in v.iter_errors(call.get("input") or {}):
            path = ".".join(str(p) for p in err.absolute_path) or "<root>"
            bad.append(f"{name}({path}): {err.message}")
    if not bad:
        return True, None
    head = bad[:10]
    tail = f"; +{len(bad) - 10} more" if len(bad) > 10 else ""
    return False, "; ".join(head) + tail
