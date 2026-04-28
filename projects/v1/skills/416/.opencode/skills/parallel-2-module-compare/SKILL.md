---
name: parallel-2-module-compare
description: Two-module API comparison workflow for the requests repo. Use when the user asks to compare the public APIs of Session and HTTPAdapter.
---

When asked to compare two module APIs:

1. **In a single assistant turn**, dispatch TWO `task` subagents
   (`subagent_type=explore`) IN PARALLEL:
   - Subagent 1: read `src/requests/sessions.py` and list the public
     method names of the `Session` class (methods that don't start with
     `_`), in source-file order.
   - Subagent 2: read `src/requests/adapters.py` and list the public
     method names of the `HTTPAdapter` class (methods that don't start
     with `_`), in source-file order.

2. After both return, write `comparison.md` at the repo root with two
   sections:

   ```
   ## Session
   <one method name per line>

   ## HTTPAdapter
   <one method name per line>
   ```

Do NOT call `read`, `grep`, or `glob` directly from the parent; only
the subagents inspect files.
