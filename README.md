# opencode-bench

A benchmark suite for evaluating the [opencode](https://github.com/nichochar/opencode) CLI agent. It tests whether the agent uses the right tools, passes correct parameters, orchestrates multi-step tasks properly, delegates to subagents, and follows project-specific instructions.

## Prerequisites

- Python 3.10+
- `opencode` CLI installed and available in `PATH`

## Quick Start

```bash
# Run all samples
python run.py

# Evaluate results
python eval.py
```

## Running Samples

`run.py` sends prompts from `samples.jsonl` to `opencode run --format json` and saves the JSON traces to `results/`.

```bash
python run.py                          # run all samples
python run.py --id 1                   # run a single sample by ID
python run.py --category tool_schema   # run all samples in a category
python run.py --clean                  # wipe results/ before running
python run.py --timeout 120            # custom per-sample timeout (default: 180s)
```

## Evaluating Results

`eval.py` replays the saved traces and checks them against the assertions defined in each sample.

```bash
python eval.py                         # evaluate all
python eval.py --id 1                  # evaluate one sample
python eval.py --category tool_schema  # evaluate a category
```

Output shows pass/fail per sample, grouped by category, with a summary score.

## Project Structure

```
samples.jsonl          # test definitions (prompts + checks)
run.py                 # runner — executes samples via opencode CLI
eval.py                # evaluator — scores traces against checks
projects/              # working directories for each sample
  default/             # shared project used by most samples
  camel_case/          # project with AGENTS.md enforcing camelCase
evaluators/            # check implementations (auto-registered)
  tool/                # tool name and parameter checks
  content/             # text and file content checks
  orchestration/       # tool ordering and parallelism checks
results/               # output traces (git-ignored)
```

## Sample Categories

| Category | What it tests |
|---|---|
| `tool_schema` | Correct tool names and parameter shapes (e.g. `filePath` not `path`) |
| `tool_orchestration` | Sequential and parallel tool usage |
| `subagent` | Delegation to explore/general subagents |
| `agents_md` | Adherence to project-level `AGENTS.md` instructions |

## Adding a Sample

Append a JSON line to `samples.jsonl`:

```json
{
  "id": 13,
  "name": "my_test",
  "category": "tool_schema",
  "project": "default",
  "prompt": "Read src/index.ts",
  "checks": [
    {"type": "any_tool_name", "equals": "read"}
  ]
}
```

### Available Check Types

**Tool checks** — verify tool usage:
- `any_tool_name` — at least one tool call matches `equals`
- `no_tool_name` — no tool call matches `not_equals`
- `any_tool_param_exists` — a tool call has the expected parameter
- `any_tool_param_absent` — a tool call does *not* have a parameter
- `any_tool_param_regex` — a tool parameter matches a regex
- `any_tool_param_value` — a tool parameter equals an exact value
- `min_tool_count` — at least N calls to a named tool

**Content checks** — verify output:
- `text_contains` — agent response contains a string
- `file_regex` — a file written by the agent matches (or doesn't match) a regex

**Orchestration checks** — verify ordering:
- `tool_before` — one tool was called before another
- `tools_same_step` — multiple tool calls happened in the same step (parallel)
