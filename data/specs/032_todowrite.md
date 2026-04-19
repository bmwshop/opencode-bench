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

## Pass criteria (5 checks)

1. `any_tool_name` equals `todowrite` -- model calls the todowrite tool
2. `max_tool_count` max 1 -- exactly one tool call (no write, read, or other tools)
3. `any_tool_param_exists` `todowrite.todos` -- provides the required todos parameter
4. `any_tool_param_array_min` `todowrite.todos` min 4 -- array contains all 4 requested items
5. `any_tool_param_array_item_fields` `todowrite.todos` fields `["content", "status", "priority"]` -- each item has the correct object shape

## Shortest path

**1 tool call**: `todowrite` with a `todos` array of 4 items. No prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Responds with a text-based bullet list instead of calling the `todowrite` tool
- Calls `todowrite` but with an empty or undersized `todos` array
- Passes a flat array of strings instead of objects with `{content, status, priority}`
- Starts executing the refactoring tasks instead of just creating the todo list
