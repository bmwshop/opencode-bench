---
name: compute-checksum
description: Compute SHA-256 checksum of a file via the bundled checksum script. Use when the user asks for a hash or checksum of a specific file.
---

Run `scripts/checksum.py <path>` (relative to the skill base directory) and
report the resulting `sha256=<hex>` line. This skill is for checksum computation
only; it does not summarize, review, or analyze file contents.
