# #10 custom_plan_prompt

## Category

plan_mode

## Project

custom_plan

## Contract

routing

## Surface

modes

## Capability

Custom plan agent prompt adherence. Opencode allows overriding the plan agent's prompt in `opencode.json` via `agent.plan.prompt`. This test verifies the model follows the custom prompt's formatting directive while still operating in plan mode. The challenge is that the built-in plan mode system reminder (`plan.txt`) contains strong read-only instructions that may overshadow the custom prompt.

## Setup

The project's `opencode.json` sets `agent.plan.prompt` to: "You are a planning assistant. Always prefix every response with [PLANNER]." Permissions allow `read`, `glob`, `grep`, `bash` only.

## Prompt (run with `--agent plan`)

> Analyze src/app.ts and suggest improvements.

## Pass criteria (1 check)

1. `text_contains` `\[PLANNER\]` -- response includes the `[PLANNER]` prefix

## Shortest path

**1 tool call**: read `src/app.ts`, then respond with the `[PLANNER]` prefix. The `read` tool has no prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Responds without `[PLANNER]` prefix -- the custom plan prompt was overshadowed by the built-in plan mode system reminder
- Ignores the custom prompt entirely and behaves like default plan mode
