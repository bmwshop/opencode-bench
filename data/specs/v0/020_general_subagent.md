# #20 general_subagent

## Category

subagent

## Contract

routing

## Surface

subagents

## Capability

Subagent routing -- using the `task` tool with `subagent_type: "general"`. The `general` agent's description says: "General-purpose agent for researching complex questions and executing multi-step tasks. Use this agent to execute multiple units of work in parallel." The prompt frames the task as two independent write operations across separate packages, naturally fitting the agent's "multiple units of work in parallel" guidance.

## Setup

The project has `packages/auth/` and `packages/payment/` with multiple source files. Neither package has a `CHANGELOG.md`.

## Prompt

> I need CHANGELOG.md files added to both packages/auth/ and packages/payment/. Each should summarize what the package does based on its source files. Delegate this.

## Pass criteria (3 checks)

1. `any_tool_name` equals `task` -- model delegates via the task tool
2. `any_tool_param_value` `task.subagent_type` equals `general` -- selects the general subagent
3. `call_schema_valid` -- all tool calls validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `task` with `subagent_type: "general"`. The "do both at the same time" framing and cross-package scope match the general agent's description of executing multiple units of work in parallel.

## Fail modes

- Performs the work directly instead of delegating (ignores the parallelism hint)
- Uses `task` with `subagent_type: "explore"` (explore is read-only, can't write files)
- Spawns two separate `task` calls instead of one general agent (not wrong, but doesn't match the check)
