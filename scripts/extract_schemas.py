#!/usr/bin/env python3
"""
Extract opencode tool schemas via its headless HTTP server.

Spawns `opencode serve --port 0` (or a caller-supplied opencode command), hits
`/experimental/tool`, writes data/tool_schemas.json. No proxy, no vendoring --
just whatever opencode binary (or source checkout) you point at.

Usage:
    # installed binary on PATH
    python scripts/extract_schemas.py

    # source checkout (has the Zod v4 fix that 1.4.0 is missing)
    python scripts/extract_schemas.py \
        --opencode "bun run /Users/me/code/opencode/packages/opencode/src/index.ts"

    # via env var (picked up by run.py / eval.py too)
    OPENCODE_BIN="bun run /path/to/packages/opencode/src/index.ts" \
        python scripts/extract_schemas.py
"""

import argparse
import json
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import opencode_meta, resolve_opencode_cmd  # noqa: E402

DEFAULT_DEST = ROOT / "data" / "tool_schemas.json"
DEFAULT_PROVIDER = "nvidia"
DEFAULT_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
LISTEN_RE = re.compile(r"listening on https?://[^:]+:(\d+)")


def _serve_and_read_port(proc, deadline_s=45):
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"opencode serve exited early: returncode={proc.returncode}"
                )
            time.sleep(0.05)
            continue
        m = LISTEN_RE.search(line)
        if m:
            return int(m.group(1))
    raise RuntimeError("opencode serve did not report a listening port")


def extract(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL, dest=None,
            opencode=None, opencode_cwd=None):
    meta = opencode_meta(opencode, opencode_cwd)
    cmd, _, cwd = resolve_opencode_cmd(opencode, opencode_cwd)

    proc = subprocess.Popen(
        [*cmd, "serve", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=cwd,
    )
    try:
        port = _serve_and_read_port(proc)
        url = f"http://localhost:{port}/experimental/tool?provider={provider}&model={model}"
        with urlopen(url, timeout=30) as r:
            tools = json.loads(r.read().decode())
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not isinstance(tools, list):
        raise RuntimeError(f"unexpected response shape: {type(tools).__name__}")

    bad = [
        t["id"] for t in tools
        if not isinstance(t.get("parameters"), dict)
        or t["parameters"].get("type") != "object"
    ]
    if bad:
        raise RuntimeError(
            "opencode returned non-object parameter schemas for tools: "
            f"{bad}. This usually means the installed opencode is older than "
            "the Zod v4 fix. Use --opencode to point at a source build."
        )

    out = {
        "opencode_version": meta["version"],
        "opencode_git": meta["git"],
        "opencode_cmd": meta["cmd"],
        "opencode_cwd": meta["cwd"],
        "opencode_executable": meta["executable"],
        "provider": provider,
        "model": model,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tools": {
            t["id"]: {"description": t.get("description", ""), "parameters": t["parameters"]}
            for t in tools
        },
    }
    dest = Path(dest) if dest else DEFAULT_DEST
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--provider", default=DEFAULT_PROVIDER)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--dest", default=str(DEFAULT_DEST))
    p.add_argument(
        "--opencode",
        default=None,
        help='opencode command (e.g. "bun run src/index.ts"). '
             "Defaults to $OPENCODE_BIN or `opencode` on PATH.",
    )
    p.add_argument(
        "--opencode-cwd",
        default=None,
        help="Working directory for opencode (needed when running from source "
             "so bun can resolve modules). Defaults to $OPENCODE_CWD or current dir.",
    )
    args = p.parse_args()

    out = extract(
        provider=args.provider,
        model=args.model,
        dest=args.dest,
        opencode=args.opencode,
        opencode_cwd=args.opencode_cwd,
    )
    g = out.get("opencode_git") or {}
    rev = f" @ {g['short']}{'+dirty' if g.get('dirty') else ''}" if g else ""
    print(
        f"Wrote {len(out['tools'])} tools for opencode {out['opencode_version']}{rev} "
        f"(cmd: {out['opencode_cmd']}) to {args.dest}"
    )


if __name__ == "__main__":
    sys.exit(main())
