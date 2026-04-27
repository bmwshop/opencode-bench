---
name: compute-checksum
description: SHA-256 checksum of a file. Use when asked to compute or report a checksum / hash of a file in the repo.
---

To compute the checksum of a file in this project:

1. Run the bundled checksum script: `scripts/checksum.py <relative-path-to-file>`
   (relative to this skill's base directory, which the `skill` tool reports back
   to you on load).

2. The script prints a line of the form `sha256=<64-hex-chars>` to stdout.
   Capture that line.

3. Report at minimum the first 6 characters of the hash to the user in your
   final reply (e.g. `3f4a8b...`).

The base directory hint from the skill-tool output tells you where `scripts/`
lives; resolve relative paths against that base.
