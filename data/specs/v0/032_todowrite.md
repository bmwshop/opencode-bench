# #32 todowrite

## Category

tool_schema

## Contract

completion

## Surface

tools

## Capability

Tool schema adherence for the `todowrite` tool. Opencode exposes a `todowrite` tool that accepts a `todos` parameter -- an array of objects each containing `content`, `status`, and `priority` fields. When explicitly asked to create a task list, the model should use `todowrite` rather than responding with plain text.

## Setup

No special project files needed beyond the project. The prompt references `src/auth.ts` which exists in the project.

## Prompt

> I need to refactor src/auth.ts. Create a todo list with these tasks: 1) Read the current auth code, 2) Extract token logic into a helper, 3) Add error handling, 4) Write tests.

## Pass criteria (4 checks)

1. `any_tool_name_recursive` equals `todowrite` -- model (or a subagent it delegates to) calls the todowrite tool
2. `any_tool_param_array_min_recursive` `todowrite.todos` min 4 -- array contains all 4 requested items, at any layer
3. `any_tool_param_array_item_fields_recursive` `todowrite.todos` fields `["content", "status", "priority"]` -- each item has the correct object shape, at any layer
4. `call_schema_valid` -- all tool calls at every layer validate against `data/tool_schemas.json`

## Shortest path

**1 tool call**: `todowrite` with a `todos` array of 4 items. No prerequisites.

## Fail modes

- Responds with a text-based bullet list instead of calling the `todowrite` tool
- Calls `todowrite` (parent or subagent) but with an empty or undersized `todos` array
- Passes a flat array of strings instead of objects with `{content, status, priority}`
- Starts executing the refactoring tasks instead of just creating the todo list
- Subagent sidecar missing, leaving a capture gap the `_recursive` checks surface as `subagent-missing`

## Notes

Delegating the todowrite call to a subagent is an unusual (and inefficient) choice for this prompt, but the recursive checks make it a legal pass: what matters is that the right tool + shape happens somewhere in the call tree.
