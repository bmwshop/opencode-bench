# #18 custom_subagent

## Category

subagent

## Contract

routing

## Surface

subagents

## Capability

Custom subagent routing (delegation choice only). Opencode allows projects to define custom subagents via `.opencode/agents/*.md` markdown files (recommended) or inline in `opencode.json`. The filename becomes the agent name, YAML frontmatter provides metadata, and the markdown body becomes the agent's custom system prompt. The model should recognize when a task matches a custom subagent's description and delegate to it using the correct `subagent_type` name. This sample tests **only** the delegation choice -- it verifies the model selects the correct custom subagent, not the outcome of the delegated task.

## Setup

The project defines a custom subagent via `.opencode/agents/reviewer.md` with description "Reviews code for bugs, security issues, and style violations. Use after writing or modifying significant code." and a dedicated review-focused system prompt. The project's `AGENTS.md` instructs: "After writing or modifying code, always delegate a review to the reviewer agent." The file `src/payment.ts` contains a payment processing function with intentional issues to review.

## Prompt

> I just rewrote src/payment.ts. Please review it for issues.

## Pass criteria (2 checks)

1. `any_tool_name` equals `task` -- model delegates via the task tool
2. `any_tool_param_value` `task.subagent_type` equals `reviewer` -- selects the custom reviewer subagent

## Shortest path

**1 tool call**: `task` with `subagent_type: "reviewer"`. No tool call checks constrain the upper bound.

## Fail modes

- Uses a built-in subagent type (`"explore"` or `"general"`) instead of the custom `"reviewer"`
- Reviews the code directly without delegating (ignores the AGENTS.md workflow instruction)
- Doesn't recognize the custom subagent exists
