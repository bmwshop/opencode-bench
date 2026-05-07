# opencode-bench

A benchmark suite for evaluating LLM compatibility with the [opencode](https://github.com/nichochar/opencode) CLI agent. It tests whether a model uses the right tools, passes correct parameters, orchestrates multi-step tasks, delegates to subagents, follows project-specific instructions, respects mode constraints, obeys tool restrictions, and invokes skills.

## Prerequisites

- Python 3.10+
- `opencode` CLI installed and available in `PATH`
- A configured model provider (the model under test)
- `pip install -r requirements.txt` (currently just `jsonschema`, used by the
  `call_schema_valid` check)

> **v1 fixtures auto-hydrate.** v1 samples target real pinned open-source repos.
> `run.py` calls `scripts/hydrate_v1_repos.py` automatically before running v1
> samples (~30s + ~200MB on first run, idempotent no-op afterwards). You don't
> need to clone with `--recurse-submodules` unless you specifically want them
> committed at the canonical `./projects/v1/` paths -- see [Workspaces, hydration,
> and parallel runs](#workspaces-hydration-and-parallel-runs) below.

## Quick Start

```bash
# Local smoke test (single sample)
python run.py --id 1
python eval.py

# Run all v1 samples against real pinned repos
python run.py

# Run a single category (e.g. code_review) for a smoke test
python run.py --category code_review

# Evaluate results (auto-detects the latest run)
python eval.py
```

## Benchmark Versions

The bench currently ships a single tier:

- **v1** — tasks against real pinned open-source repos, vendored as git submodules under [projects/v1/](projects/v1/). By default `python run.py` executes the public eval set; pass `--category all` to include the full corpus. Each repo is declared once in [data/v1_repos.json](data/v1_repos.json) with its upstream URL and exact pinned SHA. Current repos:
  - `requests` — [psf/requests](https://github.com/psf/requests)
  - `httpx` — [encode/httpx](https://github.com/encode/httpx)
  - `click` — [pallets/click](https://github.com/pallets/click)
  - `autoresearch` — [karpathy/autoresearch](https://github.com/karpathy/autoresearch)

A single run targets exactly one tier version. The `--version` argparse flag is preserved (today only `v1`); future tiers (`v1.5`, `v2`, ...) plug in by appending to `common.SAMPLES_FILES` plus the `choices=[...]` lists in `run.py`/`eval.py`/`stitch.py`.

Samples live in [data/samples_v1.jsonl](data/samples_v1.jsonl); specs live under [data/specs/v1/](data/specs/v1/).

### Adding a v1 repo

1. `git submodule add <upstream-url> projects/v1/<slug>`
2. `cd projects/v1/<slug> && git checkout <pin-sha> && cd -`
3. Declare the repo in [data/v1_repos.json](data/v1_repos.json) with `url`, `pin`, `submodule_path`, and `description`.
4. Add samples to [data/samples_v1.jsonl](data/samples_v1.jsonl) with `"version": "v1"` and `"repo": "<slug>"`.
5. `git add .gitmodules projects/v1/<slug> data/v1_repos.json data/samples_v1.jsonl && git commit`.

### Bumping a v1 pin

```bash
cd projects/v1/<slug>
git fetch && git checkout <new-sha>
cd -
# edit data/v1_repos.json -> pin: "<new-sha>"
git add projects/v1/<slug> data/v1_repos.json
git commit -m "bump <slug> pin"
```

Before running any v1 sample, `run.py` verifies the submodule HEAD matches the declared pin and aborts with an actionable hint on drift.

## Running Samples

`run.py` sends prompts from [data/samples_v1.jsonl](data/samples_v1.jsonl) to `opencode run --format json` and saves everything for that invocation under `runs/v{version}/{model_slug}/{timestamp}/`.

Each run creates an isolated directory with:

- `meta.json` — model, date, timeout, sample IDs, `version`, `v1_repo_pins`, full command-line arguments
- `scores.json` — machine-readable scores (produced by `eval.py`)
- `{id:03d}_{name}.jsonl` — per-sample opencode trace (e.g. `001_camel_case.jsonl`)
- `projects/{id:03d}/` — per-sample workspace, copied from the canonical fixture before the sample runs. Left in place after `run.py` finishes; `eval.py` deletes it by default after scoring (pass `--no-cleanup-projects` to retain it for re-scoring later)
- `captures/` (when `--proxy` is set) — proxy request/response logs for this run
- `stitched/` (after `stitch.py` runs) — stitched multi-turn traces

The canonical `projects/` tree is never modified at runtime, so it is safe to run multiple models (or the same model multiple times) in parallel.

```bash
python run.py                                              # all v1 samples; auto-allocated workspace, kept after run
python run.py --workspace .                                # legacy layout: use repo-local ./projects, ./runs, ./captures
python run.py --workspace /scratch/oc-shared               # reuse a hydrated workspace across multiple model evals
python run.py --clean-workspace                            # rm -rf the auto-allocated workspace at exit
python run.py --workspace-root /scratch                    # auto-allocate under /scratch instead of $TMPDIR (container-friendly)
python run.py --id 1                                       # run a single sample (within selected version)
python run.py --id 1 --id 2                                # run multiple samples
python run.py --category tool_schema                       # run one category
python run.py --category tool_schema --category subagent   # run multiple categories
python run.py --model provider/model-name                  # override the default model
python run.py --proxy http://localhost:4000/v1             # route through a logging proxy
python run.py --clean                                      # wipe RUNS dir first (within current workspace)
python run.py --timeout 120                                # custom per-sample timeout (default: 180s)
python run.py --retry-on-timeout 2                         # retry on TimeoutExpired (up to 2 extra attempts per sample)
python run.py -j 4                                         # run up to 4 samples in parallel (one process)
```

The `--model` flag is optional. When omitted, opencode uses its configured default and traces go under `runs/v{version}/default/{timestamp}/`. The format is `provider/model-id` (e.g. `anthropic/claude-opus-4-6`), which gets converted to a directory slug (`anthropic_claude-opus-4-6`).

## Workspaces, Hydration, and Parallel Runs

### Workspace selection

A "workspace" hosts the three mutable trees `run.py` writes to: `projects/`
(hydrated v1 fixtures), `runs/` (traces + meta), and `captures/` (proxy
payloads). Pick whichever mode fits your workflow:

| Mode | Invocation | When to use |
|---|---|---|
| **Auto-allocated** *(default)* | `python run.py ...` | Each invocation gets its own fresh `/tmp/oc-bench-XXXXXX/`. N parallel copies of `run.py` are race-free with no extra wiring. Workspace stays on disk after exit; pass `--clean-workspace` to auto-`rm`. |
| **Repo-local (legacy)** | `python run.py --workspace . ...` | Reproduces the historical layout (`./projects`, `./runs`, `./captures`). Best for everyday dev: you keep run history at familiar paths and editor/IDE search just works. |
| **Shared / persistent** | `python run.py --workspace /scratch/oc-shared ...` | Multiple model evals against the same hydrated tree. Hydration is idempotent so the second invocation is a no-op clone-wise. |

The three `OPENCODE_BENCH_PROJECTS`, `OPENCODE_BENCH_RUNS`,
`OPENCODE_BENCH_CAPTURES` env vars override the corresponding paths
individually. When any of them is pre-set, `run.py` honors it and skips both
auto-allocation and auto-cleanup. This is useful for custom wrappers or
containerized setups that need explicit mount paths.

### Hydration

v1 samples target real pinned upstream repos declared in
[data/v1_repos.json](data/v1_repos.json). `run.py` calls
[`scripts/hydrate_v1_repos.py`](scripts/hydrate_v1_repos.py) automatically
before running v1 samples — it clones each repo into the active workspace and
checks out the pinned SHA. Already-correct checkouts report `OK` and skip
(safe to call repeatedly).

Manual invocation is occasionally useful, e.g. in a staged/minimal source tree
where submodule `.git` metadata wasn't preserved:

```bash
python scripts/hydrate_v1_repos.py             # all repos
python scripts/hydrate_v1_repos.py --repo requests   # one repo
python scripts/hydrate_v1_repos.py --dry-run         # preview without modifying disk
```

If you'd rather have v1 fixtures committed in the repo (so they ship without
a network round-trip), do the manual `git submodule add` dance described
under [Adding a v1 repo](#adding-a-v1-repo) and pass `--workspace .` so
`run.py` reuses the in-tree submodules.

### Parallelism

Two independent dimensions:

- **`-j N` / `--workers N`** — within one `run.py` invocation, run up to N
  samples concurrently via a thread pool. Each sample already executes in
  its own per-sample workspace copy, so disk contention is zero. Default 1.
- **N parallel `run.py` invocations** — fire up to N processes simultaneously;
  each auto-allocates its own `/tmp/oc-bench-XXXXXX/` workspace. Zero shared
  mutable state, no wrapper script needed.

```bash
# In-process parallelism: 8 samples at a time, one workspace.
python run.py --version v1 --model X -j 8

# Multi-process parallelism: 8 isolated workspaces.
for i in 1 2 3 4 5 6 7 8; do
  python run.py --version v1 --id 91 --model X &
done; wait
```

A caveat for `--proxy` users: when combined with `-j > 1`, the switchyard
timestamp fallback used by `stitch.py` has a 3-second window, so attribution
for zero-tool-call samples may be unreliable. `run.py` prints a warning but
does not block.

### Container ephemeral-`/tmp` workaround

Inside containers `/tmp` is typically tmpfs that vanishes at container exit —
auto-allocated workspaces under `/tmp` would be lost along with their traces.
Point auto-allocation at a mounted volume instead:

```bash
# As a CLI flag
python run.py --workspace-root /scratch --id 21 --model X

# As an env var (set once, e.g. in a Dockerfile or shell profile)
OPENCODE_BENCH_WORKSPACE_ROOT=/scratch python run.py ...
```

Precedence: `--workspace-root` > `OPENCODE_BENCH_WORKSPACE_ROOT` > `$TMPDIR` >
`/tmp`. Only consulted when `run.py` auto-allocates; ignored when
`--workspace PATH` or any of the `OPENCODE_BENCH_*` path overrides are
already set.

## Evaluating Results

`eval.py` replays the saved traces and checks them against the assertions defined in each sample. It auto-discovers the latest run, or you can target a specific model or run.

```bash
python eval.py                                             # evaluate latest run (auto-detects version from meta.json)
python eval.py --version v1                                # override to force v1 scope
python eval.py --model nvidia/nemotron                     # evaluate latest run for a model
python eval.py --model nvidia/nemotron --run 2026-04-12T18-30-00  # evaluate exact run
python eval.py --list                                      # list all available runs
python eval.py --list --model nvidia/nemotron              # list runs for a model
python eval.py --id 1                                      # evaluate one sample
python eval.py --id 1 --id 2                               # evaluate multiple samples
python eval.py --category tool_schema                      # evaluate one category
python eval.py --category tool_schema --category subagent  # evaluate multiple categories
python eval.py --format json                               # machine-readable JSON output
python eval.py --format json --output scores.json          # JSON output to stdout and file
python eval.py --output scores.txt                         # text output to stdout and file
python eval.py --refresh-schemas                           # re-extract data/tool_schemas.json first
python eval.py --no-cleanup-projects                       # keep workspaces; needed for future re-scoring
```

By default `eval.py` deletes each per-sample workspace at `runs/.../projects/{NNN}/` after scoring (saves disk; repeated multi-seed sweeps can easily consume tens of GB of project copies). Pass `--no-cleanup-projects` to retain them — required if you intend to re-score the run later, since the file-graded evaluators (`exec_assert`, `exec_function`, `file_regex_disk`) read source files directly from the workspace. Trace JSONL, subagent sidecars, `captures/`, `scores.json`, and `meta.json` are always kept regardless.

When using `--format json`, the output includes a `"run"` object with the model name, date, and timestamp from `meta.json`, making each score file self-describing.

The eval header prints which opencode tool schemas it validated against, e.g.:

```
Tool schemas: opencode 1.4.0 (14 tools, extracted 2026-04-19T21:36:25+00:00)
```

### Tool schema validation (`call_schema_valid`)

Opt-in check that validates every tool call in a trace against opencode's
canonical JSON Schemas. Schemas live in `data/tool_schemas.json` and are
extracted directly from `opencode serve`'s `/experimental/tool` endpoint by
`scripts/extract_schemas.py` (checked in, versioned by `opencode_version`).

Add it to a sample's `checks` with:

```json
{"type": "call_schema_valid", "description": "all tool calls match opencode schemas"}
```

Fails on: unknown tools, missing required params, extra/misspelled params
(`filePath` vs `file_path`), and wrong parameter types. It is opt-in because
samples that exercise non-opencode tools (plugins, custom agents) would fail
spuriously.

Refresh schemas after upgrading opencode:

```bash
# installed opencode on PATH
python eval.py --refresh-schemas
# or explicitly
python scripts/extract_schemas.py

# from a source checkout (e.g. dev HEAD before a release is cut)
OPENCODE_BIN="bun run src/index.ts" \
  OPENCODE_CWD=/path/to/opencode/packages/opencode \
  python scripts/extract_schemas.py
```

Note: released opencode 1.4.0 has a Zod v4 / zod-to-json-schema bug that makes
`/experimental/tool` return `{type: "string"}` for every tool. Until the next
release, extract from a `dev` checkout using the `OPENCODE_BIN`/`OPENCODE_CWD`
form above.

Output shows scores at three levels:

- **Per sample**: checks passed / total checks, percentage score
- **Per category**: strict count, partial average, aggregate check counts
- **Overall**: strict score, partial score, total checks passed

Two scoring methods are used:

- **Strict score**: Fraction of samples where every check passed (all-or-nothing)
- **Partial score**: Average fractional score across all samples (passed checks / total checks per sample)

Both scores are reported per-category and overall.

## Proxy Mode (optional)

The benchmark works without a proxy -- `run.py` talks to your configured model provider directly. Optionally, you can route traffic through [nemo-switchyard](https://gitlab-master.nvidia.com/aire/agents/nemo-switchyard) to capture the full API payloads (system prompt, tool schemas, messages) that opencode sends to the provider.

### Terminal 1: Start the proxy

```bash
cd /path/to/nemo-switchyard
source .venv/bin/activate

export OPENAI_API_KEY="<your provider API key>"

nemo-switchyard opencode \
  --port 4000 \
  --base-url https://integrate.api.nvidia.com/v1 \
  --rl-log-dir /path/to/opencode-bench/captures
```

### Terminal 2: Run the benchmark through the proxy

```bash
python run.py --proxy http://localhost:4000/v1 --model nvidia/nvidia/nemotron-3-super-120b-a12b
```

The `--proxy` flag dynamically injects a `provider.{id}.options.baseURL` override into each sample's workspace `opencode.json` before running. Because each sample executes in a fresh copy of the canonical fixture under `runs/v{version}/{slug}/{timestamp}/projects/{id:03d}/`, the canonical `projects/` tree is never touched and the override lives only inside the run directory.

By default, the provider ID is inferred from the first segment of `--model` (e.g. `nvidia`). Override it explicitly with `--proxy-provider`:

```bash
python run.py --proxy http://localhost:4000/v1 --proxy-provider anthropic --model anthropic/claude-opus-4-6
```

When `--proxy` is set, `run.py` automatically moves new capture files from the switchyard staging directory into `runs/v{version}/{model_slug}/{timestamp}/captures/`. By default it looks for new `.json` files in `captures/` at the repo root (the `--rl-log-dir` passed to switchyard). Override with `--capture-dir` if switchyard writes elsewhere:

```bash
python run.py --proxy http://localhost:4000/v1 --capture-dir /tmp/switchyard-output --model nvidia/nvidia/nemotron-3-super-120b-a12b
```

## Project Structure

```
data/
  samples_v1.jsonl       # v1 test definitions (real-repo tasks)
  v1_repos.json          # v1 repo declarations (slug -> url, pin, submodule_path)
  tool_schemas.json      # opencode tool schemas (for call_schema_valid)
  specs/                 # per-sample documentation (capability, pass/fail criteria)
    v1/
      021_locate_cookie_tokens.md
      091_pr_review_iter_slices_yes.md
run.py                   # runner — executes samples via opencode CLI
eval.py                  # evaluator — scores traces against checks
common.py                # shared constants, sample loader, path helpers
projects/                # canonical per-sample fixtures, read-only at runtime
  v1/
    requests/            #   git submodule pinned via data/v1_repos.json
    httpx/               #   git submodule pinned via data/v1_repos.json
    click/               #   git submodule pinned via data/v1_repos.json
    autoresearch/        #   git submodule pinned via data/v1_repos.json
    skills/              #   per-skill-sample fixtures (SKILL.md + sibling scripts)
    mutants/             #   per-mutant overlay (AGENTS.md / persona / opencode.json)
    orchestration/       #   per-orchestration sample overlay
scripts/                 # eval-time / runtime / ops scripts (invoked by users)
  extract_schemas.py     # re-extracts data/tool_schemas.json from opencode serve
  hydrate_v1_repos.py    # hydrates pinned v1 repos into projects/v1/
  summarize_scores_csv.py # summarizes scores.json across runs
evaluators/              # check implementations (auto-registered)
  tool/                  # tool name and parameter checks
  content/               # text and file content checks
  orchestration/         # tool ordering and parallelism checks
runs/                    # everything produced by a run, organized by version / model / timestamp (git-ignored)
  v{version}/            #   today only v1/; future tiers (v1.5, v2, ...) plug in here
    {model_slug}/        #     e.g. nvidia_nemotron/
      {timestamp}/       #       e.g. 2026-04-12T18-30-00/
        meta.json        #         run metadata (model, date, version, v1_repo_pins, args, etc.)
        scores.json      #         machine-readable scores (produced by eval.py)
        021_locate_cookie_tokens.jsonl  # per-sample opencode trace
        091_pr_review_iter_slices_yes.jsonl
        ...
        projects/        #         per-sample workspace copies (post-run state)
          021/
          091/
          ...
        captures/        #         proxy payloads (when --proxy is used)
        stitched/        #         stitched multi-turn traces (produced by stitch.py)
captures/                # staging dir for switchyard output (git-ignored)
```

## Sample Categories

### v1

| Category | n | What it tests |
|---|---|---|
| `code_editing` | 30 | Localized behavioral change to a real Python function across `requests` / `httpx` / `click` / `autoresearch`. Easy/medium/hard tiers vary by leak (function name) + scope (single- vs multi-file). Graded by `exec_assert` against an assertion checklist. |
| `code_localization` | 30 | Find every function matching a behavior description and write `location.txt` with `file::QualifiedName` lines (lex order, anchored regex). Graded by `file_regex_disk`. |
| `code_review` | 10 | Yes/no PR judgment in plan mode. Model emits `<review>...</review>` + literal `YES`/`NO`. Graded by `text_contains` + `no_tool_name` (forbids edit/write/bash). |
| `orchestration` | 30 | Prescribed multi-step workflows — parallel dispatch, sequential chain, DAG join, merge, iteration. Graded by topology checks (`parallel_dispatch_count`, `tool_call_count`, `tool_call_sequence`, etc.) + artifact checks. |
| `skill` | 30 | Load and follow custom `SKILL.md` files. 5 internal tiers (load+follow / discovery / behavioral delta / selectivity / composition). Graded by `any_tool_param_value_recursive` + `file_regex`. |
| `tool_restriction` | 30 | Mutants of editing/localization/review samples with tool denials (`no write`, `no grep+glob`, `bash-only`, `subagent-required`). Three injection channels: system prompt, `AGENTS.md`, custom-agent persona. Graded by `no_tool_name_recursive` + parent's grader. |

## Per-Sample Documentation

Each sample has a detailed spec in `data/specs/v1/` describing the capability under test, project setup, exact prompt, pass criteria, and common failure modes. See any spec for the full format, e.g., `data/specs/v1/021_locate_cookie_tokens.md`.

## Adding a Sample

To add a new v1 sample against an existing repo, append a JSON line to `data/samples_v1.jsonl` with `"version": "v1"` and `"repo": "<slug>"`, then create a matching spec at `data/specs/v1/<NNN>_<name>.md`. To target a brand-new repo first, see [Adding a v1 repo](#adding-a-v1-repo).

The `min_calls` field is the minimum number of tool calls needed to pass all checks, respecting opencode's tool guidance (e.g. read-before-edit, prefer `edit` over `bash sed`). It is used by `eval.py` to compute the run-level efficiency metric.

### Scoring

Each sample has N checks. Two scores are computed:

- **Strict**: 1 if all N checks pass, 0 otherwise
- **Partial**: (number of passed checks) / N

Category and overall scores are averages of the per-sample scores.

### Available Check Types

**Tool checks** — verify tool usage:
- `any_tool_name` — at least one tool call matches `equals`
- `no_tool_name` — no tool call matches `not_equals`
- `any_tool_param_exists` — a tool call has the expected parameter (currently unused; `call_schema_valid` subsumes required-param presence — still available for asserting optional params)
- `any_tool_param_absent` — a tool call does *not* have a parameter
- `any_tool_param_value` — a tool parameter equals an exact value
- `any_tool_param_regex` — a tool parameter matches a regex
- `no_tool_param_value` — a tool parameter does NOT equal a forbidden value
- `min_tool_count` — at least N calls to a named tool
- `max_tool_count` — at most N tool calls (optionally filtered by tool name)
- `tool_call_count` — exactly N calls to a named tool (with optional ordering)
- `tool_call_sequence` — calls match a prescribed ordered sequence (e.g. `read → grep → write`)
- `tool_count_score` — pass if total tool calls ≤ limit; reports optimal vs actual count
- `parallel_dispatch_count` — N calls to a tool issued in a single assistant turn (e.g. `task` × 3 fan-out)
- `any_tool_param_array_min` — a tool parameter is an array with at least N items
- `any_tool_param_array_item_fields` — every item in an array parameter has the required fields
- `no_tool_any` — no tool calls were made at all (irrelevance detection)
- `call_schema_valid` — every tool call validates against `data/tool_schemas.json` (see the "Tool schema validation" section above)

Most tool checks have a paired `_recursive` variant (`any_tool_name_recursive`, `no_tool_name_recursive`, `min_tool_count_recursive`, `any_tool_param_value_recursive`, `no_tool_param_value_recursive`, `max_tool_count_recursive`, `no_tool_any_recursive`, `tool_count_score_recursive`, `any_tool_param_regex_recursive`, `any_tool_param_array_item_fields_recursive`) that walks subagent traces in addition to the parent. Use the recursive form when behavior is allowed to occur inside a delegated subagent.

**Content checks** — verify output:
- `text_contains` — agent response text matches a regex
- `text_contains_from_file` — response text mentions a value extracted from a fixture file at eval time (`source` + `extract` regex group)
- `file_regex` — content written via `write`/`edit` tools (read from trace first, falls back to disk) matches a regex
- `file_regex_disk` — content of a file on disk matches a regex (always reads disk; no trace fallback). Used by code_localization to check `location.txt` against an anchored gold regex
- `file_exists` — a file or directory exists in the project after the run
- `exec_assert` — runs Python assertions against an AST-extracted slice of a target source file. Used by code_editing to verify behavior. Supports single-file and multi-file (`targets`) shapes
- `exec_function` — runs the model's authored script in a subprocess against an AST-extracted stub of a target module, checks stdout for needles

**Orchestration checks** — verify ordering:
- `tool_before` — one tool was called before another
- `tools_same_step` — multiple tool calls occurred in the same assistant turn (parallel execution)
