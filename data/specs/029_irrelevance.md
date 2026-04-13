# #29 irrelevance

## Category

tool_schema

## Project

default

## Capability

Irrelevance detection -- recognizing when no tool is needed. When the user asks a general knowledge question that doesn't require reading or modifying project files, the model should respond in text without invoking any tool. This tests restraint: all opencode tools are visible in the system prompt, but none are relevant to the query.

This is inspired by BFCL's (Berkeley Function Calling Leaderboard) "Function Relevance Detection" category, which provides 240+ samples where the available tools are deliberately domain-adjacent but wrong for the task. In BFCL, each sample pairs a user query with misleading tool schemas (e.g., asking for the freezing point of water when only `calculate_boiling_point` is available). Since opencode-bench always exposes the full opencode toolset, we cannot control which tools are visible per sample. Instead, our irrelevance test uses a prompt that is domain-adjacent to the project context, creating a realistic temptation to use tools without any actual need.

## Design rationale

The prompt deliberately sits in an ambiguous zone:

- **Domain-adjacent**: it asks about `snake_case` vs `camelCase` -- naming conventions that are central to several opencode-bench tests (the `camel_case` project enforces camelCase, the `edit` sample checks for `oldString` not `old_string`, etc.)
- **Project-tempting**: the default project uses camelCase parameters (`filePath`, `oldString`, `newString`), and a `grep` for these patterns would return results -- making it tempting for the model to "demonstrate" with real examples
- **Pure knowledge**: despite the domain overlap, the question asks for general software engineering tradeoffs, not anything about this specific project

This is harder than an obviously off-topic question like "What is the capital of France?" because the model must distinguish between "this topic relates to the project" and "this question requires interacting with the project."

## Setup

Uses the default project. No special files needed -- the question is answerable from the model's training data alone. The default project's camelCase parameter names (`filePath`, `oldString`, `newString`) create a realistic temptation to grep or read files for examples.

## Prompt

> What are the pros and cons of using snake_case vs camelCase for API parameter names?

## Pass criteria (2 checks)

1. `no_tool_any` -- model does not call any tool
2. `text_contains` `(?i)snake.?case|camel.?case` -- response discusses both naming conventions

## Fail modes

- Calls `grep` to search for camelCase or snake_case patterns in the project -- over-eagerness to provide concrete examples from files
- Calls `read` on `AGENTS.md` or source files to check the project's conventions -- misinterprets the question as project-specific
- Calls `bash` to run a search command -- circumvents native tools but still makes an unnecessary tool call
- Calls `task` to delegate the question to an explore subagent -- unnecessary delegation for a knowledge question
- Responds correctly but also makes a spurious tool call (partial failure on `no_tool_any`)
