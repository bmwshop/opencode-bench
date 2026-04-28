---
name: iter-def-count
description: For-each-file def-count audit using bash grep. Use when the user asks to count `def` keyword occurrences across a list of Python files.
---

When asked to count `def ` keyword occurrences across a list of files:

1. For EACH file in the list, issue ONE separate `bash` call running
   `grep -c "def " <file>`. Issue exactly N bash calls (one per file),
   in the same order as the file list.

2. After all bash calls return, write `def_count.md` at the repo root
   with N lines, in the same order:

   ```
   <file_path>: <integer count>
   ```

Use the `bash` tool — NOT the `grep` tool — for the per-file counting.
No `read`, no `glob`.
