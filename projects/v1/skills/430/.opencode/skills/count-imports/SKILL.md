---
name: count-imports
description: Count top-level import statements in a Python file. Use when asked how many imports a specific Python file contains.
---

To count the top-level imports in a Python file:

1. Run the bundled script: `scripts/count_imports.py <path-to-python-file>`
   (relative to this skill's base directory, which the `skill` tool reports back
   to you on load).

2. The script prints a line of the form `import_count=<integer>` to stdout.
   Capture that line.

3. Report the count to the user in your final reply, including the literal
   `import_count=<n>` substring (so downstream tooling can parse it).

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
