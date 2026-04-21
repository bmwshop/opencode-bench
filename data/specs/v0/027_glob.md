# #27 glob

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool selection -- choosing the `glob` tool for file-pattern discovery. When asked to list files matching a naming convention, the model should use opencode's native `glob` tool rather than falling back to `bash` with `find`/`ls`, or to `grep` over file contents, or to the `task` subagent. This tests whether the model understands which opencode tool fits a filename-discovery task, and whether it surfaces the discovered paths in its response.

## Setup

The project contains test files (`src/auth.test.ts`, `src/utils.test.ts`) alongside non-test source files (`src/auth.ts`, `src/utils.ts`, `src/index.ts`). The fixture is intentionally small; the prompt is phrased to motivate filename-pattern matching rather than a directory listing or a content search.

## Prompt

> List the paths of every test file in this project.

The earlier phrasing was *"Find all test files in this project."*. It was tightened for two reasons:

- "Find" is ambiguous between name-based discovery and content-based search. The checks only reward name-based globbing (`pattern` must match `test|spec`), so a model that reasonably interpreted the task as "`grep` for `describe(`/`it(`" would fail for a non-capability reason.
- "List the paths of every test file" legitimizes echoing both filenames in the final response, which aligns the `text_contains` checks with the project's `AGENTS.md` *"Be concise. Minimize output tokens."* instruction -- models no longer have to choose between terseness and passing the response-text checks.

## Pass criteria (6 checks)

1. `any_tool_name` equals `glob` -- model calls the `glob` tool
2. `no_tool_name` not `bash` -- does not fall back to shell commands
3. `any_tool_param_regex` `glob.pattern` matches `test|spec` -- glob pattern targets test files
4. `text_contains` `auth\.test\.ts` -- response mentions auth.test.ts
5. `text_contains` `utils\.test\.ts` -- response mentions utils.test.ts
6. `call_schema_valid` -- all tool calls validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `glob` with a pattern like `**/*.test.ts`, followed by a short response that repeats the two matching paths. No prerequisites.

## Fail modes

- Uses `bash find` or `bash ls` instead of the native `glob` tool
- Uses `grep` to search for test patterns in file contents instead of discovering files by name
- Delegates to the `task` subagent instead of calling `glob` directly (observed for models that inherit `anthropic.txt`, whose guidance example routes "where is X" queries through `task`)
- Calls `glob` with a pattern that doesn't target test files (e.g., `**/*.ts` instead of `**/*.test.ts`)
- Calls `glob` correctly but ends the turn without an assistant-visible response that names the matching files (observed as an early-termination pattern on some providers)

## Notes on opencode system-prompt coverage

opencode selects a system prompt per model id in `packages/opencode/src/session/system.ts`. The prompts differ in how strongly they steer models toward `glob` for filename discovery:

- `gpt.txt`, `codex.txt`, `gemini.txt`: explicitly tell the model to prefer `Glob`/`Grep` over shell for file/text search.
- `kimi.txt`, `trinity.txt`, `agent/prompt/explore.txt`: mention `glob` as a preferred codebase-understanding tool.
- `default.txt` (used for e.g. `minimax-*`, `nemotron-*`): only mentions `glob` inside an illustrative example about writing tests; there is no explicit "prefer Glob over bash" rule.
- `anthropic.txt` (used for `claude-*`): the only `Glob` reference is an example that steers the model toward the `task` subagent *instead of* calling `Glob`/`Grep` directly.

On top of the system prompt, the `glob` tool ships its own description (`packages/opencode/src/tool/glob.txt`) which says *"Use this tool when you need to find files by name patterns"*, but it is a soft nudge rather than an exclusive preference.

As a result, part of what #27 measures is whether a given system-prompt flavor reliably routes the model to `glob` rather than pure model capability. That is a legitimate end-to-end signal for opencode-the-product, but should be kept in mind when interpreting per-model pass rates here.
