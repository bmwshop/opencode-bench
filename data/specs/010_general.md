# #10 general

**Category:** subagent
**Project:** multi_module

## Capability

Subagent delegation -- using the `task` tool with `subagent_type: "general"`. Opencode's `general` subagent has full read/write capabilities, suitable for refactoring tasks. When explicitly asked to "delegate" a write-heavy task, the model should spawn a general-purpose subagent rather than doing the work directly.

## Setup

The `multi_module` project has `packages/payment/src/` with 4 files (checkout.ts, billing.ts, refund.ts, webhook.ts), all using double quotes for strings.

## Prompt

> Every file in packages/payment/src/ uses double quotes for strings. Delegate a task to refactor all payment source files to use single quotes instead.

## Pass criteria

- Model calls the `task` tool
- Sets `subagent_type` to `"general"`

## Fail modes

- Performs the refactoring directly instead of delegating (ignores "delegate" instruction)
- Uses `task` with `subagent_type: "explore"` (explore is read-only, can't refactor)
- Uses `bash sed` to do the replacement inline
