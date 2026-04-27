---
name: api-style
description: API handler conventions for this project. Use whenever you author a new API handler / endpoint helper.
---

In this `requests` project, every NEW API-handler function must follow these
conventions:

1. Function names must be prefixed with `handle_`. Examples:
   - good: `handle_register`, `handle_login`, `handle_logout`
   - bad: `register`, `login_handler`, `do_login`

2. Each handler function must be preceded by a `# API_HANDLER` marker comment
   on its own line, immediately above the `def`.

3. Handlers should return a 2-tuple `(ok: bool, data: dict)` where `ok` is the
   success flag and `data` is the response payload.

All three rules apply together. Apply them to any handler file you create.
