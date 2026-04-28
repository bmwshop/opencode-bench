---
name: dag-response-attrs
description: Compare two attribute lists from two source files and report their overlap. Use for cross-module attribute-overlap audits.
---

When asked to compare attribute lists from two related files:

1. **In a single assistant turn**, dispatch TWO `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: list the attribute names assigned in the first
     source's relevant scope (e.g. `Response.__init__` self assignments).
   - Subagent 2: list the attribute names assigned in the second
     source's relevant scope (e.g. local-variable assignments inside
     `HTTPAdapter.build_response`).

2. After both return, write the comparison artifact (e.g.
   `attr_overlap.md`) at the repo root with three sections:

   ```
   ## __init__ attrs
   <sorted, one per line>

   ## build_response attrs
   <sorted, one per line>

   ## overlap
   <names appearing in BOTH lists, sorted, one per line>
   ```

Do NOT call `read`, `grep`, or `glob` directly from the parent; only
the subagents inspect files.
