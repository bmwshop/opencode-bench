---
name: encoding-convention
description: Bytes-decoding convention for this project. Use whenever you author a new helper that decodes bytes to str.
---

In this `httpx` project, every NEW helper that decodes bytes to str must follow
these conventions:

1. Use UTF-8 encoding with strict error handling. The exact decode call must be:
   ```python
   value.decode('utf-8', errors='strict')
   ```
   Do NOT use the default `value.decode()` (which silently allows incorrect bytes
   under some platform configurations). Do NOT use `errors='ignore'` or `'replace'`.

2. Each helper that performs a decode must be preceded by a single-line comment
   beginning with `# ENCODING:` documenting the encoding choice. Example:

   ```python
   # ENCODING: utf-8 strict
   def bytes_url_to_str(value):
       return value.decode('utf-8', errors='strict')
   ```

Both rules apply together. Apply them to any new helper file you create.
