---
name: api-style
description: API style conventions for this project. Use when creating endpoints or handlers.
---
All API handler functions in this project must:
1. Be prefixed with `handle` (e.g., `handleLogin`, `handleRegister`)
2. Include the marker comment `// API_HANDLER` above each function
3. Return objects with shape `{ ok: boolean, data: any }`
