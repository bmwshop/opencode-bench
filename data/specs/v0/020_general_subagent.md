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

> I need CHANGELOG.md files added to both packages/auth/ and packages/payment/. Each should summarize what the package does based on its source files. Hand this entire task off to a general-purpose subagent -- don't do the reads or writes yourself.

The earlier phrasing ended with just "Delegate this.", which some models interpreted as "delegate the exploration and then write yourself" -- i.e., dispatching an `explore` subagent for context and then performing the writes from the parent. The tightened wording forecloses that shortcut: the model must delegate the full task, including the writes, which requires picking a writable subagent type. `explore` is read-only, so `general` is the natural fit.

## Pass criteria (3 checks)

1. `any_tool_name` equals `task` -- model delegates via the task tool
2. `any_tool_param_value` `task.subagent_type` equals `general` -- selects the general subagent
3. `call_schema_valid` -- all tool calls validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `task` with `subagent_type: "general"`. The "do both at the same time" framing and cross-package scope match the general agent's description of executing multiple units of work in parallel.

## Fail modes

- Performs the work directly instead of delegating (ignores the "don't do the reads or writes yourself" instruction)
- Uses `task` with `subagent_type: "explore"` (explore is read-only, can't write files)
- Delegates exploration to an `explore` subagent and then writes the CHANGELOGs from the parent -- a real failure mode observed in Claude Opus 4.6 that the tightened prompt now discourages
- Spawns two separate `task` calls instead of one general agent (not wrong, but doesn't match the check)
