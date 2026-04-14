# #19 explore

## Category

subagent

## Project

multi_module

## Capability

Subagent delegation -- using the `task` tool with `subagent_type: "explore"`. Opencode provides a built-in `explore` subagent optimized for read-only codebase exploration. When asked to investigate or summarize a subsystem, the model should delegate to this subagent rather than manually reading files one by one.

## Setup

The `multi_module` project has a realistic multi-package structure with `packages/auth/src/` containing 4 files (login.ts, token.ts, session.ts, middleware.ts) that form an interconnected authentication system.

## Prompt

> Explore the authentication system in packages/auth/ and give me a comprehensive summary of how login, tokens, sessions, and middleware work together.

## Pass criteria (2 checks)

1. `any_tool_name` equals `task` -- model delegates via the task tool
2. `any_tool_param_value` `task.subagent_type` equals `explore` -- selects the explore subagent

## Shortest path

**1 tool call**: `task` with `subagent_type: "explore"`. No tool call checks constrain the upper bound.

## Fail modes

- Manually reads files one by one instead of delegating to the explore subagent
- Uses `task` but with wrong subagent type (e.g., `"general"`)
- Doesn't delegate at all and attempts to answer from context alone
