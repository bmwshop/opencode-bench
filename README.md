# opencode-bench

A benchmark suite for evaluating LLM compatibility with the [opencode](https://github.com/nichochar/opencode) CLI agent. It tests whether a model uses the right tools, passes correct parameters, orchestrates multi-step tasks, delegates to subagents, follows project-specific instructions, respects mode constraints, obeys tool restrictions, and invokes skills.

## Prerequisites

- Python 3.10+
- `opencode` CLI installed and available in `PATH`
- A configured model provider (the model under test)

## Quick Start

```bash
# Run all samples
python run.py

# Evaluate results
python eval.py
```

## Running Samples

`run.py` sends prompts from `data/samples.jsonl` to `opencode run --format json` and saves everything for that invocation under `runs/{model_slug}/{timestamp}/`.

Each run creates an isolated directory with:

- `meta.json` — model, date, timeout, sample IDs, full command-line arguments
- `{id}_{name}.jsonl` — per-sample opencode trace
- `projects/{id:03d}/` — per-sample workspace, copied from `projects/{id:03d}/` before the sample runs and left in place afterwards for inspection
- `captures/` (when `--proxy` is set) — proxy request/response logs moved here after the run
- `stitched/` (after `stitch.py` runs) — stitched multi-turn traces

The canonical `projects/` tree is never modified at runtime, so it is safe to run multiple models (or the same model multiple times) in parallel.

```bash
python run.py                                              # run all samples
python run.py --id 1                                       # run a single sample
python run.py --id 1 --id 2                                # run multiple samples
python run.py --category tool_schema                       # run one category
python run.py --category tool_schema --category subagent   # run multiple categories
python run.py --model provider/model-name                  # override the default model
python run.py --proxy http://localhost:4000/v1             # route through a logging proxy
python run.py --clean                                      # wipe runs/ first
python run.py --timeout 120                                # custom per-sample timeout (default: 180s)
python run.py -j 4                                         # run up to 4 samples in parallel
```

The `--model` flag is optional. When omitted, opencode uses its configured default and traces go under `runs/default/`. The format is `provider/model-id` (e.g. `anthropic/claude-opus-4-6`), which gets converted to a directory slug (`anthropic_claude-opus-4-6`).

`--workers` / `-j` (default 1) runs samples in parallel via a thread pool. Each sample already executes in its own `runs/{slug}/{ts}/projects/{id:03d}/` workspace copy, so parallelism is safe with no contention on disk. Combined with `--proxy`, the switchyard timestamp fallback used by `stitch.py` has a 3-second window, so attribution for zero-tool-call samples may be unreliable — `run.py` prints a warning but does not block it.

## Evaluating Results

`eval.py` replays the saved traces and checks them against the assertions defined in each sample. It auto-discovers the latest run, or you can target a specific model or run.

```bash
python eval.py                                             # evaluate latest run (any model)
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
```

When using `--format json`, the output includes a `"run"` object with the model name, date, and timestamp from `meta.json`, making each score file self-describing.

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

The `--proxy` flag dynamically injects a `provider.{id}.options.baseURL` override into each sample's workspace `opencode.json` before running. Because each sample executes in a fresh copy of `projects/{id:03d}/` under `runs/{slug}/{timestamp}/projects/`, the canonical `projects/` tree is never touched and the override lives only inside the run directory.

By default, the provider ID is inferred from the first segment of `--model` (e.g. `nvidia`). Override it explicitly with `--proxy-provider`:

```bash
python run.py --proxy http://localhost:4000/v1 --proxy-provider anthropic --model anthropic/claude-opus-4-6
```

When `--proxy` is set, `run.py` automatically moves new capture files from the switchyard staging directory into `runs/{model_slug}/{timestamp}/captures/`. By default it looks for new `.json` files in `captures/` at the repo root (the `--rl-log-dir` passed to switchyard). Override with `--capture-dir` if switchyard writes elsewhere:

```bash
python run.py --proxy http://localhost:4000/v1 --capture-dir /tmp/switchyard-output --model nvidia/nvidia/nemotron-3-super-120b-a12b
```

## Project Structure

```
data/
  samples.jsonl          # test definitions (prompts + checks)
  specs/                 # per-sample documentation (capability, pass/fail criteria)
    001_camel_case.md
    ...
    033_write.md
run.py                   # runner — executes samples via opencode CLI
eval.py                  # evaluator — scores traces against checks
common.py                # shared constants and sample loader
projects/                # canonical per-sample fixtures, read-only at runtime
  001/                   #   fixture for sample #1
  002/                   #   fixture for sample #2
  ...
  033/                   #   fixture for sample #33
scripts/
  flatten_projects.py    # one-time migration that built the per-sample layout
evaluators/              # check implementations (auto-registered)
  tool/                  # tool name and parameter checks
  content/               # text and file content checks
  orchestration/         # tool ordering and parallelism checks
runs/                    # everything produced by a run, organized by model and timestamp (git-ignored)
  {model_slug}/          #   e.g. nvidia_nemotron/
    {timestamp}/         #     e.g. 2026-04-12T18-30-00/
      meta.json          #       run metadata (model, date, args, etc.)
      1_camel_case.jsonl #       per-sample opencode trace
      ...
      projects/          #       per-sample workspace copies (post-run state)
        001/
        ...
      captures/          #       proxy payloads (when --proxy is used)
      stitched/          #       stitched multi-turn traces (produced by stitch.py)
      scores.json        #       machine-readable scores (produced by eval.py)
captures/                # staging dir for switchyard output (git-ignored)
```

## Sample Categories

| Category | Samples | What it tests |
|---|---|---|
| `agents_md` | #1-2 | Adherence to project-level `AGENTS.md` instructions and custom primary agent prompts |
| `distractor` | #3-5 | Precision under noise — file listing, verbose context, and misleading causal narratives |
| `efficiency` | #6-8 | Minimal tool usage — batch replacements, direct file creation, and single-step text replacement |
| `plan_mode` | #9-11 | Plan mode read-only enforcement, custom plan agent prompts, and refusal to edit when asked in plan mode |
| `prompt_tool_restriction` | #12-14 | Obeying prompt-based instructions to use only `bash` when all tools are visible |
| `skill` | #15-17 | Discovering and invoking skills: knowledge-based conventions, multi-step workflows, and code-backed scripts |
| `subagent` | #18-21 | Delegation to built-in subagents (`explore`, `general`), parallel subagent spawning, and custom subagent invocation |
| `system_tool_restriction` | #22 | Adapting to a reduced toolset when tools are hidden via permission config |
| `tool_orchestration` | #23-24 | Sequential tool chaining (read then edit) and parallel tool execution (two reads in one step) |
| `tool_schema` | #25-33 | Correct tool names and parameter shapes, and irrelevance detection (e.g., `filePath` not `path`, `oldString` not `old_string`) |

## Contract Types

Each sample has a `contract` field that declares what the checks verify:

| Contract | Count | Meaning |
|---|---|---|
| `completion` | 26 | Checks verify the actual task outcome — file content on disk, extracted values in response, correct tool arguments, or correct command execution |
| `routing` | 7 | Checks verify only the delegation or prompt-adherence choice — correct tool/subagent selected, correct prefix in response — without validating the outcome of the delegated work |

Routing samples: #2, #9, #10, #18, #19, #20, #21. All other samples are completion.

This distinction is useful for stratified scoring: routing tests measure whether the model *knows which tool to use*, while completion tests measure whether it *uses the tool correctly*.

## Surface Types

Each sample has a `surface` field identifying the opencode capability being tested:

| Surface | Count | What it covers |
|---|---|---|
| `tools` | 17 | Core tool usage — correct tool selection, parameter schemas, parallel/sequential orchestration, distractor resistance, efficiency, and irrelevance detection |
| `agents` | 2 | Project-level `AGENTS.md` instruction following and custom primary agent prompts |
| `modes` | 3 | Plan mode constraints — read-only enforcement, custom plan agent prompts, refusal to edit |
| `permissions` | 4 | Tool restriction adherence — prompt-based (`bash_only`) and system-level (permission config) |
| `skills` | 3 | Skill discovery and invocation — knowledge-based conventions, multi-step workflows, code-backed scripts |
| `subagents` | 4 | Delegation to subagents — built-in (`explore`, `general`), custom, and parallel spawning |

## Per-Sample Documentation

Each sample has a detailed spec in `data/specs/` describing the capability under test, project setup, exact prompt, pass criteria, and common failure modes. See any spec for the full format, e.g., `data/specs/001_camel_case.md`.

## Adding a Sample

1. Append a JSON line to `data/samples.jsonl`:

```json
{
  "id": 34,
  "name": "my_test",
  "category": "tool_schema",
  "contract": "completion",
  "surface": "tools",
  "min_calls": 1,
  "prompt": "Read src/index.ts",
  "checks": [
    {"type": "any_tool_name", "equals": "read"}
  ]
}
```

The `min_calls` field is the minimum number of tool calls needed to pass all checks, respecting opencode's tool guidance (e.g. read-before-edit, prefer `edit` over `bash sed`). It is used by `stitch.py` to compute optimality of traced runs.

2. Create a matching spec at `data/specs/034_my_test.md`.

3. Create the sample's project fixture at `projects/034/` with an `opencode.json` (at minimum `{"permission": {"*": "allow"}}` to auto-approve tool use). Each sample gets its own directory; if two samples need similar fixtures, duplicate them — per-sample isolation is intentional and also lets each fixture carry its own fresh UUIDs. This directory is read-only at runtime: `run.py` copies it into `runs/.../projects/034/` before executing opencode.

### Scoring

Each sample has N checks. Two scores are computed:

- **Strict**: 1 if all N checks pass, 0 otherwise
- **Partial**: (number of passed checks) / N

Category and overall scores are averages of the per-sample scores.

### Available Check Types

**Tool checks** — verify tool usage:
- `any_tool_name` — at least one tool call matches `equals`
- `no_tool_name` — no tool call matches `not_equals`
- `any_tool_param_exists` — a tool call has the expected parameter
- `any_tool_param_absent` — a tool call does *not* have a parameter
- `any_tool_param_value` — a tool parameter equals an exact value
- `any_tool_param_regex` — a tool parameter matches a regex
- `min_tool_count` — at least N calls to a named tool
- `max_tool_count` — at most N tool calls (optionally filtered by tool name)
- `tool_count_score` — pass if total tool calls ≤ limit; reports optimal vs actual count
- `any_tool_param_array_min` — a tool parameter is an array with at least N items
- `any_tool_param_array_item_fields` — every item in an array parameter has the required fields
- `no_tool_any` — no tool calls were made at all (irrelevance detection)

**Content checks** — verify output:
- `text_contains` — agent response text matches a regex
- `file_regex` — content written via `write`/`edit` tools (or existing on disk) matches a regex
- `file_exists` — a file or directory exists in the project after the run

**Orchestration checks** — verify ordering:
- `tool_before` — one tool was called before another
- `tools_same_step` — multiple tool calls occurred in the same assistant turn (parallel execution)
