# #11 parallel

## Category

subagent

## Project

multi_module

## Capability

Parallel subagent delegation -- spawning multiple `task` calls in a single step. Opencode supports parallel tool calls, and this extends to subagent delegation. When two independent investigations are requested simultaneously, the model should spawn both subagents in the same turn rather than waiting for one to complete before starting the other.

## Setup

The `multi_module` project has two distinct packages: `packages/auth/` (authentication) and `packages/payment/` (payment processing), each with 4 source files.

## Prompt

> I need two independent investigations done simultaneously: (1) explore the authentication system in packages/auth/, and (2) explore the payment processing pipeline in packages/payment/. Do both at the same time.

## Pass criteria (2 checks)

1. `min_tool_count` `task` >= 2 -- at least two task calls in the trace
2. `tools_same_step` `task` >= 2 -- both tasks spawned in the same assistant turn

## Fail modes

- Spawns subagents sequentially in different steps (ignores "simultaneously" / "at the same time")
- Only spawns one subagent and handles the other investigation directly
- Doesn't delegate at all and reads files manually
