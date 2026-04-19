"""
Validate every tool call in a trace against opencode's canonical JSON Schemas.

Schemas come from `data/tool_schemas.json`, extracted by `scripts/extract_schemas.py`
(also reachable via `python eval.py --refresh-schemas`). Extra/missing/misspelled
parameters, wrong types, and calls to tools that aren't in opencode all fail the
check. This is therefore opt-in per sample: don't add it to samples that
intentionally exercise non-opencode tools (plugins, custom agents, etc.).
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
def check(tools, texts, chk):
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
