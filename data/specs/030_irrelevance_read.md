# #30 irrelevance_read

## Category

tool_schema

## Project

default

## Capability

Targeted irrelevance detection -- resisting the temptation to call `read` when the question is about general concepts, not this project's files. This is a harder variant of #29 (`irrelevance`): the prompt names a function (`verify`) and module type (`auth module`) that both literally exist in the project's `src/auth.ts`, creating a strong false signal that the model should read that file.

## Design rationale

The default project contains `src/auth.ts` with a `verify` function that checks a token against a constant. The prompt asks "How does a typical verify function in an auth module validate tokens?" -- this is clearly a general knowledge question (note "a typical"), but every keyword maps to something in the project:

- "verify" matches the `verify()` function in `src/auth.ts`
- "auth module" matches the filename `auth.ts`
- "tokens" matches the `TOKEN` import from `utils.ts`

This mirrors BFCL's hardest irrelevance samples where the available tools are domain-adjacent but semantically wrong for the task. In our case, the `read` tool is domain-adjacent (it could read `auth.ts`) but wrong for the task (the user is asking for general knowledge, not this project's code).

## Setup

Uses the default project. The file `src/auth.ts` contains:

```ts
import { TOKEN } from './utils'

export function verify(input: string) {
  return input === TOKEN
}
```

This creates maximum temptation: every noun in the prompt has a concrete match in the project.

## Prompt

> How does a typical verify function in an auth module validate tokens?

## Pass criteria (2 checks)

1. `no_tool_any` -- model does not call any tool
2. `text_contains` `(?i)token|verif|auth` -- response discusses token verification concepts

## Shortest path

**0 tool calls**: answer from general knowledge. The `no_tool_any` check enforces no tool usage. The question asks about "a typical" verify function, not this project's specific one.

## Fail modes

- Calls `read` on `src/auth.ts` -- the most likely failure; the model sees matching keywords and reads the file instead of answering from knowledge
- Calls `grep` for "verify" or "token" -- searching the project for examples when none are needed
- Calls `task` to delegate exploration of the auth module -- unnecessary delegation
- Answers correctly about the project's specific `verify` function rather than general patterns -- indicates the model read the file or inferred from context rather than answering generically
