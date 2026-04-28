---
name: naming-convention
description: In-house naming convention for new helper files in this project. Use whenever you author a new top-level Python helper.
---

In this `autoresearch` project, every NEW helper file (and every NEW top-level
function added to an existing file) must follow these conventions:

1. Top-level function names must be prefixed with `_az_`. Examples:
   - good: `_az_compute_step_count`, `_az_load_shard`
   - bad: `compute_step_count`, `load_shard`

2. Each function must be preceded by a single-line marker comment `# AZ_HELPER`
   on its own line, immediately above the `def`.

Both rules apply together: a function without the prefix OR without the marker
fails the convention. Apply them to any file you create.
