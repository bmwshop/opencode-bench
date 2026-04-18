#!/usr/bin/env python3
"""
Stitch proxy capture files into per-sample multi-turn traces.

Joins runs/{slug}/{ts}/captures/ (full API request/response pairs) with
runs/{slug}/{ts}/{id}_{name}.jsonl (opencode event traces) using the callID
linkage:

    trace tool_use.callID == capture response.tool_calls[].id

Output goes to runs/{slug}/{ts}/stitched/ with one JSON file per sample.

Usage:
    python stitch.py                         # stitch latest run
    python stitch.py --model nvidia/nvidia/nemotron-3-super-120b-a12b
    python stitch.py --model nvidia/nvidia/nemotron-3-super-120b-a12b --id 1
    python stitch.py --model nvidia/nvidia/nemotron-3-super-120b-a12b --pass-only
"""

import json
import sys
import argparse
from datetime import datetime
from common import load, resolve_run


_TITLE_SYSTEM = "You are a title generator"


def _is_title_call(cap):
    """Detect opencode's internal title-generation API calls."""
    msgs = cap.get("request", {}).get("messages", [])
    if msgs and msgs[0].get("role") == "system":
        return msgs[0].get("content", "").startswith(_TITLE_SYSTEM)
    return False


def _load_captures(cap_dir):
    """Load all capture files and build a tool_call_id -> capture index."""
    caps = {}
    tc_index = {}
    skipped = 0
    for p in sorted(cap_dir.iterdir()):
        if not p.suffix == ".json":
            continue
        d = json.loads(p.read_text())
        if _is_title_call(d):
            skipped += 1
            continue
        caps[p.name] = d
        tcs = d["response"]["choices"][0]["message"].get("tool_calls") or []
        for tc in tcs:
            tc_index[tc["id"]] = p.name
    return caps, tc_index, skipped


def _trace_callids(trace_path):
    """Extract ordered callIDs and timestamp range from a result trace."""
    ids = []
    ts_min = float("inf")
    ts_max = 0
    for line in trace_path.read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        ts = ev.get("timestamp", 0)
        if ts:
            ts_min = min(ts_min, ts)
            ts_max = max(ts_max, ts)
        if ev["type"] == "tool_use":
            ids.append(ev["part"]["callID"])
    return ids, (ts_min, ts_max)


def _find_final(caps, seen, last_callid):
    """Find the text-only capture that follows the last tool call."""
    for name, d in caps.items():
        if name in seen:
            continue
        for m in d["request"]["messages"]:
            if m.get("role") == "tool" and m.get("tool_call_id") == last_callid:
                return name
    return None


def _find_by_timestamp(caps, seen, ts_range):
    """Fallback for zero-tool samples: match by timestamp proximity."""
    ts_min, _ = ts_range
    best = None
    best_dist = float("inf")
    for name, d in caps.items():
        if name in seen:
            continue
        cap_ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
        epoch_ms = int(cap_ts.timestamp() * 1000)
        dist = abs(epoch_ms - ts_min)
        if dist > 3000:
            continue
        msgs = d["request"]["messages"]
        if msgs[-1].get("role") != "user":
            continue
        if dist < best_dist:
            best = name
            best_dist = dist
    return best


def _extract_messages(ordered, caps):
    """Build a flat message list from ordered capture filenames."""
    messages = []
    prev = 0
    for i, name in enumerate(ordered):
        d = caps[name]
        msgs = d["request"]["messages"]
        resp = d["response"]["choices"][0]["message"]

        if i == 0:
            for m in msgs[1:]:
                messages.append(m)
        else:
            for m in msgs[prev:]:
                if m.get("role") == "assistant":
                    continue
                messages.append(m)

        assistant = {"role": "assistant"}
        reasoning = resp.get("reasoning_content")
        if reasoning:
            assistant["reasoning_content"] = reasoning
        if resp.get("tool_calls"):
            assistant["content"] = resp.get("content")
            assistant["tool_calls"] = resp["tool_calls"]
        else:
            assistant["content"] = resp.get("content", "")
        messages.append(assistant)

        prev = len(msgs)
    return messages


def stitch(sample, run_dir, caps, tc_index, scores):
    """Stitch captures for a single sample. Returns the trace dict or None."""
    sid = sample["id"]
    name = sample.get("name", str(sid))
    trace_file = None
    for p in run_dir.iterdir():
        if p.name.startswith(f"{sid}_") and p.suffix == ".jsonl":
            trace_file = p
            break

    if not trace_file or not trace_file.exists():
        return None

    call_ids, ts_range = _trace_callids(trace_file)

    ordered = []
    seen = set()
    for cid in call_ids:
        if cid in tc_index:
            cf = tc_index[cid]
            if cf not in seen:
                seen.add(cf)
                ordered.append(cf)

    if call_ids:
        final = _find_final(caps, seen, call_ids[-1])
        if final:
            ordered.append(final)
            seen.add(final)
    else:
        match = _find_by_timestamp(caps, seen, ts_range)
        if match:
            ordered.append(match)
            seen.add(match)

    if not ordered:
        return None

    first = caps[ordered[0]]
    system = first["request"]["messages"][0]["content"]
    tools = first["request"].get("tools") or []
    messages = _extract_messages(ordered, caps)

    score_entry = scores.get(sid, {})
    tc = sum(len(m["tool_calls"]) for m in messages if m["role"] == "assistant" and m.get("tool_calls"))
    sp = sample.get("min_calls")
    passed = score_entry.get("pass", False)
    optimal = passed and sp is not None and tc == sp

    return {
        "sample_id": sid,
        "sample_name": name,
        "category": sample.get("category"),
        "contract": sample.get("contract"),
        "surface": sample.get("surface"),
        "model": first["request"].get("model"),
        "pass": score_entry.get("pass", None),
        "score": score_entry.get("score", None),
        "tool_calls": tc,
        "min_calls": sp,
        "optimal": optimal,
        "system": system,
        "tools": tools,
        "messages": messages,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", "-m", help="Model in provider/model format (default: latest run)")
    parser.add_argument("--id", action="append", help="Stitch specific sample(s) by ID")
    parser.add_argument("--category", action="append", help="Stitch samples in a category")
    parser.add_argument("--pass-only", action="store_true", help="Only emit strictly-passing samples")
    parser.add_argument("--run", help="Specific run timestamp (default: latest)")
    args = parser.parse_args()

    run_dir = resolve_run(args.model, args.run)
    if not run_dir:
        print(f"ERROR: no run found for model={args.model}")
        sys.exit(1)

    cap_dir = run_dir / "captures"
    if not cap_dir.is_dir():
        print(f"ERROR: no captures at {cap_dir}")
        sys.exit(1)

    scores_path = run_dir / "scores.json"
    scores = {}
    if scores_path.exists():
        raw = json.loads(scores_path.read_text())
        for s in raw.get("samples", []):
            label = s["label"]
            sid = int(label.split("#")[1].split(" ")[0])
            scores[sid] = s

    print(f"Loading captures from {cap_dir}")
    caps, tc_index, title_skipped = _load_captures(cap_dir)
    print(f"  {len(caps)} captures, {len(tc_index)} tool_call entries indexed ({title_skipped} title calls filtered)")

    samples = list(load(args))
    if not samples:
        print("No matching samples found.")
        sys.exit(1)

    out_dir = run_dir / "stitched"
    if out_dir.is_dir():
        for old in out_dir.glob("*.json"):
            old.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    stitched = 0
    skipped = 0
    for sample in samples:
        sid = sample["id"]
        name = sample.get("name", str(sid))

        if args.pass_only:
            entry = scores.get(sid, {})
            if not entry.get("pass", False):
                skipped += 1
                continue

        result = stitch(sample, run_dir, caps, tc_index, scores)
        if not result:
            print(f"  SKIP #{sid} {name}: no captures found")
            skipped += 1
            continue

        out = out_dir / f"{sid}_{name}.json"
        out.write_text(json.dumps(result, indent=2) + "\n")
        n = len(result["messages"])
        tag = " *" if result["optimal"] else ""
        print(f"  #{sid} {name}: {n} messages, {result['tool_calls']} tc{tag} -> {out.name}")
        stitched += 1

    print(f"\nDone. {stitched} stitched, {skipped} skipped")
    print(f"Output: {out_dir}/")


if __name__ == "__main__":
    main()
