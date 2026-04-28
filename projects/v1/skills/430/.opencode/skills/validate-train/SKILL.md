---
name: validate-train
description: Project validation workflow. Use when asked to validate or check this autoresearch project; runs the bundled validation script and reports its output code.
---

To validate this project:

1. Run the bundled validation script: `scripts/validate.py` (relative to this
   skill's base directory, which the `skill` tool reports back to you on load).

2. The script prints a single line of the form `VALID_<8-hex-chars>` to stdout.
   Capture that token.

3. Report the captured token verbatim to the user in your final reply.

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
