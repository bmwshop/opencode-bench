# Archetype 04 — `parallel_subagents`

## Description

In OpenCode (an agentic CLI similar to Claude Code), the assistant can emit several `task` tool calls in a SINGLE response; the calls run concurrently and results return together. This archetype covers requests that decompose into multiple INDEPENDENT sub-tasks the assistant should fan out via parallel `task` calls. Independence matters: no ordering, no shared state, no result needed by another sub-task. Vanilla OpenCode setup (no custom subagents defined) — the assistant uses the built-in `explore` subagent for these calls.

Common shapes:

- **Per-unit understanding** — independently investigate, review, audit, or summarize each unit
- **Per-unit application** — apply the same edit or generation per unit
- **Cross-unit comparison** — how does each unit handle X, which is best/safest/most efficient

The fanout signal can be EXPLICIT ("in parallel", "concurrently", "simultaneously") or IMPLICIT via distributive phrasing ("for each", "every", or naming N independent units like "auth, billing, notifications"). Both are realistic; vary across them. Counts can be explicit, implicit-from-naming, or absent (assistant enumerates targets first).

## Output fields

Output a JSON object with these fields:

- `"question"`: string — phrased so multiple independent sub-tasks are clearly required (explicit parallelism words, "for each" / "every" distributive phrasing, or a list of named independent units).
- `"pre_command"`: string — bash to create the project structure with the independent modules/files/dirs the question references. Each unit should have non-trivial content.

## Examples (5)

### Example 1

```
question: Take a look at the auth/, billing/, and notifications/ services in this repo and tell me which ones are pinning outdated dependencies that should be bumped.

pre_command:

mkdir -p auth billing notifications && cat > auth/package.json << 'EOF'
{
  "name": "auth",
  "version": "1.4.0",
  "dependencies": {
    "express": "4.17.1",
    "jsonwebtoken": "8.5.1",
    "bcrypt": "5.0.1"
  }
}
EOF
cat > billing/requirements.txt << 'EOF'
flask==1.1.2
stripe==4.0.0
requests==2.25.1
EOF
cat > notifications/go.mod << 'EOF'
module example.com/notifications

go 1.18

require (
    github.com/sendgrid/sendgrid-go v3.10.0
    github.com/twilio/twilio-go v0.16.0
)
EOF
```

### Example 2

```
question: For each Dockerfile under services/, check whether it pins a specific Python version (not just python:3) and report the ones that don't.

pre_command:

mkdir -p services/api services/worker services/scheduler services/notifier && cat > services/api/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "api"]
EOF
cat > services/worker/Dockerfile << 'EOF'
FROM python:3
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "worker.py"]
EOF
cat > services/scheduler/Dockerfile << 'EOF'
FROM python:3.10
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "-m", "scheduler"]
EOF
cat > services/notifier/Dockerfile << 'EOF'
FROM python:latest
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "notifier.py"]
EOF
```

### Example 3

```
question: Look at internal/api/middleware.go and internal/admin/middleware.go at the same time and tell me which one applies stricter rate-limiting and how the two configurations differ.

pre_command:

mkdir -p internal/api internal/admin && cat > internal/api/middleware.go << 'EOF'
package api

import (
    "net/http"
    "time"
    "golang.org/x/time/rate"
)

var limiter = rate.NewLimiter(rate.Every(time.Second), 100)

func RateLimit(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if !limiter.Allow() {
            http.Error(w, "too many requests", http.StatusTooManyRequests)
            return
        }
        next.ServeHTTP(w, r)
    })
}
EOF
cat > internal/admin/middleware.go << 'EOF'
package admin

import (
    "net/http"
    "sync"
    "time"
    "golang.org/x/time/rate"
)

var (
    mu       sync.Mutex
    limiters = map[string]*rate.Limiter{}
)

func getLimiter(ip string) *rate.Limiter {
    mu.Lock()
    defer mu.Unlock()
    if l, ok := limiters[ip]; ok { return l }
    l := rate.NewLimiter(rate.Every(5*time.Second), 5)
    limiters[ip] = l
    return l
}

func RateLimit(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if !getLimiter(r.RemoteAddr).Allow() {
            http.Error(w, "too many requests", http.StatusTooManyRequests)
            return
        }
        next.ServeHTTP(w, r)
    })
}
EOF
```

### Example 4

```
question: Add a structured-logging line at the start of each request handler in the auth/, billing/, cart/, and inventory/ services so every incoming request is logged with method and path.

pre_command:

mkdir -p auth billing cart inventory && cat > auth/handler.py << 'EOF'
from flask import Blueprint, request, jsonify

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    return jsonify({'token': 'tok_' + data['user']})

@bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'ok': True})
EOF
cat > billing/handler.py << 'EOF'
from flask import Blueprint, request, jsonify

bp = Blueprint('billing', __name__)

@bp.route('/charge', methods=['POST'])
def charge():
    data = request.get_json()
    return jsonify({'charge_id': 'ch_' + data['user']})
EOF
cat > cart/handler.py << 'EOF'
from flask import Blueprint, request, jsonify

bp = Blueprint('cart', __name__)

@bp.route('/items', methods=['GET'])
def list_items():
    return jsonify({'items': []})

@bp.route('/items', methods=['POST'])
def add_item():
    return jsonify({'ok': True})
EOF
cat > inventory/handler.py << 'EOF'
from flask import Blueprint, request, jsonify

bp = Blueprint('inventory', __name__)

@bp.route('/stock/<sku>', methods=['GET'])
def stock(sku):
    return jsonify({'sku': sku, 'qty': 0})
EOF
```

### Example 5

```
question: Concurrently write a smoke test for every public route registered in cmd/api/routes.go — each test should hit the route and assert a 2xx response.

pre_command:

mkdir -p cmd/api && cat > cmd/api/routes.go << 'EOF'
package main

import (
    "encoding/json"
    "net/http"
)

func registerRoutes(mux *http.ServeMux) {
    mux.HandleFunc("/health", health)
    mux.HandleFunc("/api/users", listUsers)
    mux.HandleFunc("/api/orders", listOrders)
    mux.HandleFunc("/api/items", listItems)
    mux.HandleFunc("/api/stats", stats)
}

func health(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func listUsers(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode([]string{})
}

func listOrders(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode([]string{})
}

func listItems(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode([]string{})
}

func stats(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode(map[string]int{"requests": 0})
}
EOF
cat > cmd/api/main.go << 'EOF'
package main

import (
    "net/http"
)

func main() {
    mux := http.NewServeMux()
    registerRoutes(mux)
    http.ListenAndServe(":8080", mux)
}
EOF
cat > go.mod << 'EOF'
module example.com/api

go 1.21
EOF
```

## Overlap notes

All five examples use synthetic services (`auth/`, `billing/`, `notifications/`, `cart/`, `inventory/`, `services/api`, `services/worker`, etc.). None of the function names (`RateLimit`, `getLimiter`, `health`, `listUsers`, `add_item`, `stock`) are present in v1 benchmark samples, and none of the directory layouts mirror the benchmark's `requests/`, `httpx/`, `click/`, or `autoresearch/` topology.
