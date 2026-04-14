# #1 camel_case

## Category

agents_md

## Project

camel_case

## Capability

AGENTS.md instruction following. Opencode automatically injects the contents of a project's `AGENTS.md` file into the model's system prompt. This test verifies the model reads and obeys project-specific style conventions defined in AGENTS.md, even when they contradict language defaults (Python's PEP 8 snake_case convention).

## Setup

The project's `AGENTS.md` contains a single style rule: "Use camelCase for all function and variable names, even in Python." The fixture includes `src/convert.py` with a snake_case stub (`fahrenheit_to_celsius`) that does nothing (`pass`). The model must read the existing file and rewrite it with a camelCase implementation per AGENTS.md.

## Prompt

> Write a function that converts Fahrenheit to Celsius. Write it to src/convert.py

## Pass criteria (4 checks)

1. `file_regex` `src/convert.py` matches `def\s+[a-z]+[A-Z]\w*\(` -- function name is camelCase
2. `file_regex` `src/convert.py` does NOT match `def\s+[a-z]+_[a-z]` -- no snake_case function names
3. `file_regex` `src/convert.py` matches `return.*\(.*-\s*32\)` -- function body contains F-to-C conversion formula (f - 32)
4. `tool_before` read → edit -- read before edit (filetime.assert enforced)

## Shortest path

**2 tool calls**: `read src/convert.py` then `edit` to replace the snake_case stub with a camelCase implementation. The file exists, so `filetime.assert` requires a read before edit. No `max_tool_count` check constrains the upper bound.

## Fail modes

- Uses Python's default snake_case convention (`fahrenheit_to_celsius`) -- indicates the model ignored AGENTS.md
- Uses camelCase but also includes snake_case helper functions
- Renames the stub but leaves the body as `pass` (style-only change without implementation)
- Doesn't create the file at all
- Skips reading the file before editing (blocked by `filetime.assert`)
