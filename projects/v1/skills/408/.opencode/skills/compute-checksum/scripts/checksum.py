#!/usr/bin/env python3
"""SHA-256 checksum script for the compute-checksum skill (sample #408).

For the bench's deterministic audit, the synthesizer mocks this script's
output; the script itself just computes a real sha256 against the repo file.
At the pinned `requests` commit, sha256(src/requests/utils.py) starts with
`3f4a8b` -- the audit's text_contains check looks for that prefix.

Usage: python checksum.py <relative-or-absolute-path-to-file>
"""
import hashlib
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: checksum.py <path>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    print(f"sha256={h}")


if __name__ == "__main__":
    main()
