---
name: ghi-004
description: Encoding-convention rules for new bytes-handling helpers. Use when authoring a new helper that converts between bytes and str.
---

Any new bytes-handling helper must:

- Use `value.decode('utf-8', errors='strict')`.
- Be preceded by a `# ENCODING:` marker comment documenting the encoding choice.
