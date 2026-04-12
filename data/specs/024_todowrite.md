# #24 todowrite

## Category

tool_schema

## Project

default

## Capability

Tool schema adherence for the `todowrite` tool. Opencode exposes a `todowrite` tool that accepts a `todos` parameter -- an array of objects each containing `content`, `status`, and `priority` fields. When explicitly asked to create a task list, the model should use `todowrite` rather than responding with plain text.

## Setup

No special project files needed beyond the default project. The prompt references `src/auth.ts` which exists in the default project.

## Prompt

> I need to refactor src/auth.ts. Create a todo list with these tasks: 1) Read the current auth code, 2) Extract token logic into a helper, 3) Add error handling, 4) Write tests.

## Pass criteria (5 checks)

1. `any_tool_name` equals `todowrite` -- model calls the todowrite tool
2. `no_tool_name` not equals `write` -- does not write a todo file instead of calling the tool
3. `any_tool_param_exists` `todowrite.todos` -- provides the required todos parameter
4. `any_tool_param_array_min` `todowrite.todos` min 3 -- array contains at least 3 items
5. `any_tool_param_array_item_fields` `todowrite.todos` fields `["content", "status", "priority"]` -- each item has the correct object shape

## Fail modes

- Responds with a text-based bullet list instead of calling the `todowrite` tool
- Calls `todowrite` but with an empty or undersized `todos` array
- Passes a flat array of strings instead of objects with `{content, status, priority}`
- Starts executing the refactoring tasks instead of just creating the todo list
