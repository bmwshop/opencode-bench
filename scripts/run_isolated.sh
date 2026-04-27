#!/bin/bash
# scripts/run_isolated.sh - run a benchmark inside an isolated workspace.
#
# Each invocation routes ALL mutable state under a unique $WORKSPACE tree:
#
#   $WS/projects/v1/<repo>/    hydrated fixtures (cloned per-invocation)
#   $WS/runs/                  trace + meta outputs
#   $WS/captures/              capture staging
#
# Bench code (data/, scripts/, evaluators/) stays at the canonical location;
# only mutable state moves under $WS. N parallel invocations -> N isolated
# trees, zero shared mutable state.
#
# Usage:
#
#   # Fresh workspace under /tmp/oc-bench-XXXXXX, auto-cleaned on exit:
#   bash scripts/run_isolated.sh -- --version v1 --category code_review --model X
#
#   # Specified workspace, kept after run for inspection:
#   OC_KEEP_WORKSPACE=1 bash scripts/run_isolated.sh /scratch/oc-foo \
#     --version v1 --id 91 --model X
#
#   # 8 parallel invocations on the same machine:
#   for i in 1 2 3 4 5 6 7 8; do
#     bash scripts/run_isolated.sh --version v1 --id 91 --model X &
#   done; wait
#
# Notes:
#
# - The first positional arg, if present and starting with `/` or `~`, is
#   treated as the workspace dir; otherwise a fresh mktemp dir is allocated.
#   All other args are forwarded verbatim to run.py.
# - Hydration runs once per invocation (~30s, ~200MB per workspace for the
#   four pinned v1 repos). If disk/network is constrained, the hydrator
#   could later be extended with `git clone --reference=<bare-clone>` to
#   share git objects across workspaces; not in scope here.
# - SIGKILL escapes the EXIT trap; in that case the workspace leaks and you
#   should `rm -rf` it manually. SIGINT/SIGTERM are caught.

set -euo pipefail

# Resolve the bench checkout root (parent of scripts/) so this script can be
# launched from any cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# First positional arg is the workspace if it starts with `/` or `~/`; else
# allocate a fresh mktemp dir. Either way, the remaining args go to run.py.
if [[ $# -gt 0 && ( "$1" == /* || "$1" == "~/"* ) ]]; then
    WORKSPACE="$1"; shift
elif [[ $# -gt 0 && "$1" == "--" ]]; then
    shift
    WORKSPACE="$(mktemp -d "${TMPDIR:-/tmp}/oc-bench-XXXXXX")"
else
    WORKSPACE="$(mktemp -d "${TMPDIR:-/tmp}/oc-bench-XXXXXX")"
fi

# Expand `~/` if present.
WORKSPACE="${WORKSPACE/#\~\//$HOME/}"

KEEP="${OC_KEEP_WORKSPACE:-0}"
if [[ "$KEEP" != "1" ]]; then
    trap 'rm -rf "$WORKSPACE"' EXIT INT TERM
fi

export OPENCODE_BENCH_PROJECTS="$WORKSPACE/projects"
export OPENCODE_BENCH_RUNS="$WORKSPACE/runs"
export OPENCODE_BENCH_CAPTURES="$WORKSPACE/captures"

mkdir -p "$OPENCODE_BENCH_PROJECTS" "$OPENCODE_BENCH_RUNS" "$OPENCODE_BENCH_CAPTURES"

echo "[run_isolated] workspace=$WORKSPACE"
echo "[run_isolated] OPENCODE_BENCH_PROJECTS=$OPENCODE_BENCH_PROJECTS"
echo "[run_isolated] OPENCODE_BENCH_RUNS=$OPENCODE_BENCH_RUNS"
echo "[run_isolated] OPENCODE_BENCH_CAPTURES=$OPENCODE_BENCH_CAPTURES"
echo "[run_isolated] hydrating v1 repos..."
python3 "$BENCH_ROOT/scripts/hydrate_v1_repos.py"

echo "[run_isolated] running benchmark..."
python3 "$BENCH_ROOT/run.py" "$@"

echo "[run_isolated] done."
if [[ "$KEEP" == "1" ]]; then
    echo "[run_isolated] workspace kept at $WORKSPACE (OC_KEEP_WORKSPACE=1)"
fi
