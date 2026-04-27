## Tool Restriction

All file reading and grepping must be delegated to a subagent via the `task` tool. The parent must not call read, grep, or glob directly; you may still call `edit` on the parent. To inspect any file, dispatch a subagent via `task` (e.g. with `subagent_type="explore"`) and use the subagent's returned summary.
