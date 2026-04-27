## Tool Restriction

All file reading and grepping must be delegated to a subagent via the `task` tool. The parent must not call read, grep, or glob directly; the parent's role is to issue the review verdict in its final response based on subagent-returned summaries. Dispatch a subagent via `task` (e.g. with `subagent_type="explore"`) for every file inspection.
