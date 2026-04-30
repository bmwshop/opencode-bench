# Archetype 06 — `plan_mode`

## Description

In OpenCode (an agentic CLI similar to Claude Code), 'plan mode' is a built-in mode the user activates with `--agent plan` or `default_agent: plan`. In plan mode the assistant receives an automatically-injected system reminder that forbids any file modification and any non-readonly shell command — it may only read, search, and analyse, then produce a written plan.

Common plan-mode request types:

- **Refactor plan** — propose how to restructure code, files to change, edits per file
- **Dependency upgrade plan** — major version bump, breaking-change list, rollout order
- **Architecture review** — propose splitting a monolith / extracting services
- **Security audit plan** — areas to audit, threat model, prioritised findings
- **Performance investigation** — hypotheses, what to measure, profiling plan
- **Migration plan** — moving from framework A to B, db schema migration
- **Test-coverage plan** — what to add, in what order, what frameworks
- **Observability / monitoring plan** — what metrics/traces/logs to add
- **Build / CI overhaul plan** — propose new pipeline steps, caching strategy

The deliverable is the written plan; the user reviews it before any edits happen.

## Output fields

Output a JSON object with these fields:

- `"question"`: string — asks for analysis/planning. The deliverable is a written plan; do not ask the assistant to "also apply" or "implement".
- `"pre_command"`: string — bash to create a realistic project (at least 2-3 files, ~10+ lines each) with non-trivial code worth analysing.

## Examples (3)

### Example 1

```
question: I want to migrate this Express app from callback-style middleware to async/await. Produce a step-by-step plan: which files need to change, the specific edits for each, the migration risks, a test strategy, and a safe rollout order. Do not apply any edits.

pre_command:

mkdir -p src/middleware src/routes && cat > src/middleware/auth.js << 'EOF'
const jwt = require('jsonwebtoken');
module.exports = function(req, res, next) {
  const h = req.headers.authorization;
  if (!h) return res.status(401).json({ error: 'no token' });
  jwt.verify(h.slice(7), process.env.SECRET, (err, decoded) => {
    if (err) return res.status(401).json({ error: 'invalid' });
    req.user = decoded;
    next();
  });
};
EOF
cat > src/middleware/logger.js << 'EOF'
const fs = require('fs');
module.exports = function(req, res, next) {
  fs.appendFile('access.log', `${new Date().toISOString()} ${req.method} ${req.url}\n`, err => {
    if (err) console.error(err);
    next();
  });
};
EOF
cat > src/routes/orders.js << 'EOF'
const express = require('express');
const r = express.Router();
const auth = require('../middleware/auth');
const db = require('../db');
r.get('/', auth, (req, res) => {
  db.query('SELECT * FROM orders WHERE user_id = $1', [req.user.id], (err, rows) => {
    if (err) return res.status(500).json({ error: 'db' });
    res.json(rows);
  });
});
module.exports = r;
EOF
```

### Example 2

```
question: We're on Django 3.2 and we want to get to Django 5.0. Walk me through what needs to change: the breaking changes that affect this codebase, the migration order, the risks for each step, and a rollback plan if it goes wrong. Don't make any edits.

pre_command:

mkdir -p myproj/users myproj/orders && cat > myproj/settings.py << 'EOF'
import os

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'myproj.users',
    'myproj.orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

DATABASES = { 'default': { 'ENGINE': 'django.db.backends.postgresql', 'NAME': 'myproj' } }

USE_L10N = True
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
EOF
cat > myproj/users/models.py << 'EOF'
from django.db import models
from django.utils.encoding import smart_text

class User(models.Model):
    email = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    def __str__(self):
        return smart_text(self.name)
EOF
cat > myproj/orders/views.py << 'EOF'
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _
from .models import Order

@csrf_exempt
def list_orders(request):
    orders = Order.objects.all()
    return render(request, 'orders/list.html', { 'orders': orders, 'title': _('Your orders') })
EOF
cat > myproj/orders/models.py << 'EOF'
from django.db import models

class Order(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    total_cents = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
EOF
cat > requirements.txt << 'EOF'
Django==3.2.20
psycopg2-binary==2.9.6
EOF
```

### Example 3

```
question: Look at the current monolith under src/ and propose how we'd split it into 3-4 focused services. I want to see the proposed service boundaries, the data each owns, the inter-service contracts, and what we'd need to change to extract them in a safe order. No code changes — just the proposal.

pre_command:

mkdir -p src/api src/billing src/users src/notify && cat > src/api/server.py << 'EOF'
from flask import Flask, request, jsonify
from .. import users, billing, notify

app = Flask(__name__)

@app.post('/users')
def create_user():
    u = users.create(request.json['email'], request.json['name'])
    notify.send_welcome(u.email)
    return jsonify({ 'id': u.id })

@app.post('/orders')
def create_order():
    user_id = request.headers['X-User-Id']
    invoice = billing.charge(user_id, request.json['amount_cents'])
    notify.send_receipt(user_id, invoice.id)
    return jsonify({ 'invoice_id': invoice.id })

@app.get('/users/<uid>/invoices')
def list_invoices(uid):
    return jsonify([{ 'id': i.id, 'amount': i.amount } for i in billing.list_for(uid)])
EOF
cat > src/users/__init__.py << 'EOF'
from dataclasses import dataclass

@dataclass
class User:
    id: str
    email: str
    name: str

_USERS: dict[str, User] = {}

def create(email: str, name: str) -> User:
    uid = f'u_{len(_USERS) + 1}'
    u = User(uid, email, name)
    _USERS[uid] = u
    return u

def get(uid: str) -> User: return _USERS[uid]
EOF
cat > src/billing/__init__.py << 'EOF'
from dataclasses import dataclass

@dataclass
class Invoice:
    id: str
    user_id: str
    amount: int

_INVOICES: list[Invoice] = []

def charge(user_id: str, amount_cents: int) -> Invoice:
    inv = Invoice(f'inv_{len(_INVOICES) + 1}', user_id, amount_cents)
    _INVOICES.append(inv)
    return inv

def list_for(user_id: str) -> list[Invoice]:
    return [i for i in _INVOICES if i.user_id == user_id]
EOF
cat > src/notify/__init__.py << 'EOF'
def send_welcome(email: str) -> None: print(f'welcome -> {email}')
def send_receipt(user_id: str, invoice_id: str) -> None: print(f'receipt {invoice_id} -> {user_id}')
EOF
```

## Overlap notes

Three synthetic projects: an Express callback-middleware app, a Django 3.2 codebase, and a small Flask monolith. None of these reference v1 benchmark function names or files. The deliverable is always a written plan — no edits — which matches plan-mode's read-only system-reminder.
