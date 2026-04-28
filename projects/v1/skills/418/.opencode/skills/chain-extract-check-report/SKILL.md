---
name: chain-extract-check-report
description: Extract-check-report workflow that audits whether each function from one file is referenced from another. Use for cross-module-coverage audits.
---

When asked to check whether each function in one file is referenced
from another:

1. **Read** the source file (e.g. `src/requests/api.py`) to identify
   the top-level function names.
2. For EACH identified function name, issue ONE separate `grep` call
   searching the consumer file (e.g. `src/requests/sessions.py`) for
   the function name. Issue exactly N grep calls (one per function),
   in the order the functions appear in the source.
3. Write `coverage.md` at the repo root with one line per function in
   the same order:

   ```
   <function_name>: used        (if grep returned >=1 match)
   <function_name>: unused      (otherwise)
   ```

No `glob` and no extra `read` calls beyond step 1.
