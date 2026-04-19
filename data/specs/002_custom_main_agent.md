# #2 custom_main_agent

## Category

agents_md

## Contract

routing

## Surface

agents

## Capability

Custom primary agent prompt adherence. Opencode allows projects to define custom primary agents via `.opencode/agents/*.md` markdown files (recommended) or inline in `opencode.json`, selectable via `opencode run --agent <name>`. The filename becomes the agent name, YAML frontmatter provides metadata, and the markdown body becomes the agent's custom system prompt. This test verifies the model follows instructions from a custom agent's prompt, specifically a formatting directive that should appear in every response.

## Setup

The project defines a primary agent via `.opencode/agents/auditor.md` with prompt: "You are a security auditor. Always prefix every response with [AUDITOR]." The file `src/app.ts` contains a simple login function with an obvious security issue (credentials in plain text).

## Prompt (run with `--agent auditor`)

> Review src/app.ts for security issues.

## Pass criteria (2 checks)

1. `any_tool_name` equals `read` -- model reads the file before reviewing
2. `text_contains` `\[AUDITOR\]` -- response includes the `[AUDITOR]` prefix

## Shortest path

**1 tool call**: read `src/app.ts`, then respond with the `[AUDITOR]` prefix. The prompt asks to review a specific file, so the model must read it. The `read` tool has no prerequisites. No tool call checks constrain the upper bound.

## Fail modes

- Responds without the `[AUDITOR]` prefix -- indicates the custom agent prompt was ignored
- Prefixes with something else (e.g., `[SECURITY]`) -- misinterprets the instruction
- Responds about security issues without reading `src/app.ts` first -- hallucinates instead of inspecting the code
