# Archetype 07 — `simple_tool_use`

## Description

A request whose natural fulfilment is a SINGLE tool call — an unambiguous semantic match between the request and one of the assistant's tools (`read`, `write`, `bash`, `glob`, `grep`, `edit`). Vary which tool a given question naturally calls for across samples — read a file, write a new file, run a shell command, find files by glob pattern, search file contents with grep, or edit one specific value in an existing file. The phrasing should make the right tool obvious without naming it.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — naturally requires one tool call. Don't name the tool.
- `"pre_command"`: string — bash to create any files/dirs the question references.

## Examples (3)

### Example 1

```
question: What's the current default value of MAX_RETRIES in config/retry.py?

pre_command:

mkdir -p config && cat > config/retry.py << 'EOF'
from enum import Enum

MAX_RETRIES = 3
BACKOFF_BASE_MS = 250
TIMEOUT_SEC = 30

class RetryPolicy(Enum):
    EXPONENTIAL = 'exp'
    LINEAR = 'lin'
EOF
```

### Example 2

```
question: Find every place in the codebase where we still import from the deprecated legacy_logger module.

pre_command:

mkdir -p src && cat > src/app.py << 'EOF'
from legacy_logger import log
from .utils import helper

def main():
    log('starting')
    helper()
EOF
cat > src/db.py << 'EOF'
import os
from legacy_logger import log

def connect():
    log('connect')
    return os.environ.get('DATABASE_URL')
EOF
cat > src/utils.py << 'EOF'
def helper(): return 42
EOF
cat > src/cli.py << 'EOF'
import sys
from legacy_logger import log

def run(): log(f'args={sys.argv}')
EOF
cat > src/metrics.py << 'EOF'
import time
def tick(): return time.monotonic()
EOF
```

### Example 3

```
question: In src/config.ts, change BASE_URL from "http://api.example.com" to "https://api.example.com".

pre_command:

mkdir -p src && cat > src/config.ts << 'EOF'
export const BASE_URL = "http://api.example.com";
export const TIMEOUT_MS = 5000;
export const RETRIES = 3;
EOF
```

## Overlap notes

Synthetic constants (`MAX_RETRIES`, `BASE_URL`), synthetic deprecated module (`legacy_logger`), generic project layout. No collision with v1 benchmark function names or scenarios.
