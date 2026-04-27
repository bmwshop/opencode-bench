---
name: summary-flow
description: Module function-count summary workflow. Use when the user asks for a summary of how many top-level def definitions a Python file contains.
---

When asked to summarize a Python file's function count, follow these steps in order:

1. Read the target file using the `read` tool.
2. Count the lines that begin with `def ` at column 0 (top-level function definitions).
   Do NOT count indented `def ` lines (those are nested inside classes or functions).
3. Write `summary.md` at the repo root with this exact format:

   ```
   # Summary: <basename of target file>
   ## Function Count: <integer>
   ```

The `# Summary:` heading and `## Function Count:` subheading are required substrings;
the hidden grader checks for both. The basename should appear without any directory
prefix (e.g. `_utils.py`, not `httpx/_utils.py`).
