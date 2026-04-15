# #20 general_subagent

## Category

subagent

## Project

multi_module

## Contract

routing

## Surface

subagents

## Capability

Subagent routing -- using the `task` tool with `subagent_type: "general"`. The `general` agent's description says: "General-purpose agent for researching complex questions and executing multi-step tasks. Use this agent to execute multiple units of work in parallel." The prompt frames the task as two independent write operations across separate packages, naturally fitting the agent's "multiple units of work in parallel" guidance.

The previous version of this sample asked the model to "delegate a task to refactor" which conflicted with the `task` tool's guidance ("When NOT to use: Other tasks that are not related to the agent descriptions above"). This version uses a prompt that aligns with the `general` agent's stated purpose.

## Setup

The `multi_module` project has `packages/auth/` and `packages/payment/` with multiple source files. Neither package has a `CHANGELOG.md`.

## Prompt

> I need CHANGELOG.md files added to both packages/auth/ and packages/payment/. Each should summarize what the package does based on its source files. Delegate this.

## Pass criteria (2 checks)

1. `any_tool_name` equals `task` -- model delegates via the task tool
2. `any_tool_param_value` `task.subagent_type` equals `general` -- selects the general subagent

## Shortest path

**1 tool call**: `task` with `subagent_type: "general"`. The "do both at the same time" framing and cross-package scope match the general agent's description of executing multiple units of work in parallel.

## Fail modes

- Performs the work directly instead of delegating (ignores the parallelism hint)
- Uses `task` with `subagent_type: "explore"` (explore is read-only, can't write files)
- Spawns two separate `task` calls instead of one general agent (not wrong, but doesn't match the check)
