# #2 custom_main_agent

## Category

agents_md

## Project

custom_main_agent

## Capability

Custom primary agent prompt adherence. Opencode allows projects to define custom primary agents in `opencode.json` with custom system prompts, selectable via `opencode run --agent <name>`. This test verifies the model follows instructions from a custom agent's prompt, specifically a formatting directive that should appear in every response.

## Setup

The project's `opencode.json` defines a primary agent named `"auditor"` with prompt: "You are a security auditor. Always prefix every response with [AUDITOR]." The file `src/app.ts` contains a simple login function with an obvious security issue (credentials in plain text).

## Prompt (run with `--agent auditor`)

> Review src/app.ts for security issues.

## Pass criteria (1 check)

1. `text_contains` `\[AUDITOR\]` -- response includes the `[AUDITOR]` prefix

## Fail modes

- Responds without the `[AUDITOR]` prefix -- indicates the custom agent prompt was ignored
- Prefixes with something else (e.g., `[SECURITY]`) -- misinterprets the instruction
