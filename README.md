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

`run.py` sends prompts from `data/samples.jsonl` to `opencode run --format json` and saves JSON traces to `results/`.

```bash
python run.py                                              # run all samples
python run.py --id 1                                       # run a single sample
python run.py --id 1 --id 2                                # run multiple samples
python run.py --category tool_schema                       # run one category
python run.py --category tool_schema --category subagent   # run multiple categories
python run.py --model provider/model-name                  # override the default model
python run.py --clean                                      # wipe results/ before running
python run.py --timeout 120                                # custom per-sample timeout (default: 180s)
```

The `--model` flag is optional. When omitted, opencode uses its configured default. The format is `provider/model-id` (e.g. `anthropic/claude-opus-4-6`).

## Evaluating Results

`eval.py` replays the saved traces and checks them against the assertions defined in each sample.

```bash
python eval.py                                             # evaluate all
python eval.py --id 1                                      # evaluate one sample
python eval.py --id 1 --id 2                               # evaluate multiple samples
python eval.py --category tool_schema                      # evaluate one category
python eval.py --category tool_schema --category subagent  # evaluate multiple categories
python eval.py --format json                               # machine-readable JSON output
python eval.py --format json --output scores.json          # JSON output to stdout and file
python eval.py --output scores.txt                         # text output to stdout and file
```

Output shows scores at three levels:

- **Per sample**: checks passed / total checks, percentage score
- **Per category**: strict count, partial average, aggregate check counts
- **Overall**: strict score, partial score, total checks passed

Two scoring methods are used:

- **Strict score**: Fraction of samples where every check passed (all-or-nothing)
- **Partial score**: Average fractional score across all samples (passed checks / total checks per sample)

Both scores are reported per-category and overall.

## Project Structure

```
data/
  samples.jsonl          # test definitions (prompts + checks)
  specs/                 # per-sample documentation (capability, pass/fail criteria)
    001_read.md
    ...
    024_code_backed.md
run.py                   # runner — executes samples via opencode CLI
eval.py                  # evaluator — scores traces against checks
common.py                # shared constants and sample loader
projects/                # working directories for each sample
  default/               # shared project for tool_schema and tool_orchestration tests
  multi_module/          # multi-package project for subagent delegation tests
  camel_case/            # AGENTS.md enforcing camelCase naming
  custom_subagent/       # custom reviewer subagent defined in opencode.json
  custom_main_agent/     # custom primary agent with [AUDITOR] prefix
  plan_default/          # plan mode with restricted edit permissions
  custom_plan/           # custom plan agent prompt with [PLANNER] prefix
  bash_only/             # prompt-based bash-only tool restriction
  bash_strict/           # system-level tool restriction via permissions
  skill_knowledge/       # knowledge-based skill (api-style conventions)
  skill_workflow/        # workflow-based skill (review steps)
  skill_code/            # code-backed skill (validate.sh script)
evaluators/              # check implementations (auto-registered)
  tool/                  # tool name and parameter checks
  content/               # text and file content checks
  orchestration/         # tool ordering and parallelism checks
results/                 # output traces (git-ignored)
```

## Sample Categories

| Category | Samples | What it tests |
|---|---|---|
| `tool_schema` | #1-6 | Correct tool names and parameter shapes (e.g., `filePath` not `path`, `oldString` not `old_string`) |
| `tool_orchestration` | #7-8 | Sequential tool chaining (read then edit) and parallel tool execution (two reads in one step) |
| `subagent` | #9-12 | Delegation to built-in subagents (`explore`, `general`), parallel subagent spawning, and custom subagent invocation |
| `agents_md` | #13-14 | Adherence to project-level `AGENTS.md` instructions and custom primary agent prompts |
| `plan_mode` | #15-17 | Plan mode read-only enforcement, plan file creation in `.opencode/plans/`, and custom plan agent prompts |
| `prompt_tool_restriction` | #18-20 | Obeying prompt-based instructions to use only `bash` when all tools are visible |
| `system_tool_restriction` | #21 | Adapting to a reduced toolset when tools are hidden via permission config |
| `skill` | #22-24 | Discovering and invoking skills: knowledge-based conventions, multi-step workflows, and code-backed scripts |

## Per-Sample Documentation

Each sample has a detailed spec in `data/specs/` describing the capability under test, project setup, exact prompt, pass criteria, and common failure modes. See any spec for the full format, e.g., `data/specs/001_read.md`.

## Adding a Sample

1. Append a JSON line to `data/samples.jsonl`:

```json
{
  "id": 25,
  "name": "my_test",
  "category": "tool_schema",
  "project": "default",
  "prompt": "Read src/index.ts",
  "checks": [
    {"type": "any_tool_name", "equals": "read"}
  ]
}
```

2. Create a matching spec at `data/specs/025_my_test.md`.

3. If the test needs a custom project environment, create it under `projects/` with an `opencode.json` (at minimum `{"permission": {"*": "allow"}}` to auto-approve tool use).

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

**Content checks** — verify output:
- `text_contains` — agent response text matches a regex
- `file_regex` — content written via `write`/`edit` tools (or existing on disk) matches a regex
- `file_exists` — a file or directory exists in the project after the run

**Orchestration checks** — verify ordering:
- `tool_before` — one tool was called before another
- `tools_same_step` — multiple tool calls occurred in the same assistant turn (parallel execution)
