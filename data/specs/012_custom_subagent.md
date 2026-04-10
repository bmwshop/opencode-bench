# #12 custom_subagent

## Category

subagent

## Project

custom_subagent

## Capability

Custom subagent invocation. Opencode allows projects to define custom subagents in `opencode.json` with specific names, descriptions, and modes. The model should recognize when a task matches a custom subagent's description and delegate to it using the correct `subagent_type` name. This tests the model's ability to discover and use project-specific agent configurations.

## Setup

The project's `opencode.json` defines a custom subagent named `"reviewer"` with description "Reviews code for bugs, security issues, and style violations. Use after writing or modifying significant code." The project's `AGENTS.md` instructs: "After writing or modifying code, always delegate a review to the reviewer agent." The file `src/payment.ts` contains a payment processing function with intentional issues to review.

## Prompt

> I just rewrote src/payment.ts. Please review it for issues.

## Pass criteria (2 checks)

1. `any_tool_name` equals `task` -- model delegates via the task tool
2. `any_tool_param_value` `task.subagent_type` equals `reviewer` -- selects the custom reviewer subagent

## Fail modes

- Uses a built-in subagent type (`"explore"` or `"general"`) instead of the custom `"reviewer"`
- Reviews the code directly without delegating (ignores the AGENTS.md workflow instruction)
- Doesn't recognize the custom subagent exists
