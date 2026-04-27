#!/usr/bin/env python3
"""Top-level import counter for the count-imports skill (sample #409).

Counts lines that start with `import ` or `from ` at column 0 (top-level imports).
At the pinned httpx commit, httpx/_utils.py has 7 such lines; the audit's
text_contains check looks for `import_count=7`.

Usage: python count_imports.py <path-to-python-file>
"""
import re
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: count_imports.py <path>", file=sys.stderr)
        sys.exit(2)
    pattern = re.compile(r"^(import|from)\s+", re.MULTILINE)
    with open(sys.argv[1]) as f:
        n = len(pattern.findall(f.read()))
    print(f"import_count={n}")


if __name__ == "__main__":
    main()
