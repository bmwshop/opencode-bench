---
name: iter-helper-callers
description: For-each-helper caller-count audit using grep. Use when the user asks to count callers of a list of helpers in a specific consumer file.
---

When asked to count callers of a list of helpers in a specific
consumer file:

1. For EACH helper name in the list, issue ONE separate `grep` call
   searching the consumer file for the helper name. Issue exactly N
   grep calls (one per helper), in the same order as the helper list.

2. After all grep calls return, write the report file (e.g.
   `caller_table.md`) at the repo root with N lines, in the same order:

   ```
   <helper_name>: <integer count>
   ```

Use the `grep` tool — exactly N times. No `bash`, no `read`, no `glob`.
