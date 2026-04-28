---
name: count-imports
description: Count top-level import statements in a Python file via the bundled count-imports script. Use when asked specifically how many imports a Python file has.
---

Run `scripts/count_imports.py <path>` (relative to the skill base directory) and
report the resulting `import_count=<n>` line. This skill counts imports only;
it does not summarize, review, or analyze file contents.
