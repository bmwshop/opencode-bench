# Review: src/app.ts

## TODO Count: 2

## Issues

- **Missing input validation**: The `process` function accepts a `data` parameter but does not validate it before parsing. This could cause runtime errors if invalid JSON is passed.
- **No error handling**: The `JSON.parse` call can throw if `data` is not valid JSON. There's no try/catch to handle this gracefully.