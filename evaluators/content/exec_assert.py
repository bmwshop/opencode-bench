"""
exec_assert: run a list of Python assertion expressions against symbols
AST-extracted from a target source file.

The extraction + execution happens in an isolated `python3` subprocess so
the target module's side-effectful imports (e.g. `import torch`,
`from kernels import get_kernel`) are never triggered. Only the names
listed in `chk["constants"]` (bound via `ast.literal_eval`),
`chk["functions"]` (exec'd from `ast.get_source_segment`), and
`chk["imports"]` (plain `__import__`) are loaded into the namespace the
asserts run against.

Per-check granularity: one `exec_assert` invocation reports exactly one
pass/fail. All asserts must pass. On failure, the reason names the first
failing assert (or the harness-level error that blocked it).

Each assert is `{"expr": "..."}` and optionally `{"setup": "stmt", "expr": "..."}`.
When `setup` is present, `exec(setup, ns)` runs before `eval(expr, ns)`.
`setup` mutates the shared namespace, so e.g. `SCHEDULE = "cosine"` on one
assert persists into subsequent asserts unless overridden.
"""
import json
import subprocess
import sys
from pathlib import Path

from evaluators import register


_HARNESS = r'''
import ast, json, sys

def _find_const_value(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return node.value
        elif (isinstance(node, ast.AnnAssign)
              and isinstance(node.target, ast.Name)
              and node.target.id == name
              and node.value is not None):
            return node.value
    return None

def _find_func_node(tree, name):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None

def _run(config):
    path = config["path"]
    asserts = config.get("asserts", []) or []

    try:
        with open(path, "r") as f:
            src = f.read()
    except FileNotFoundError:
        return {"ok": False, "reason": f"file not found: {path}"}
    except OSError as e:
        return {"ok": False, "reason": f"could not read {path}: {e}"}

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"ok": False, "reason": f"SyntaxError at line {e.lineno}: {e.msg}"}

    ns = {}

    for name in config.get("constants", []) or []:
        value_node = _find_const_value(tree, name)
        if value_node is None:
            return {"ok": False, "reason": f"constant {name!r} not found"}
        try:
            ns[name] = ast.literal_eval(value_node)
        except (ValueError, SyntaxError) as e:
            return {"ok": False, "reason": f"constant {name!r} not a literal: {e}"}

    for mod_name in config.get("imports", []) or []:
        try:
            ns[mod_name] = __import__(mod_name)
        except ImportError as e:
            return {"ok": False, "reason": f"import {mod_name!r} failed: {e}"}

    for name in config.get("functions", []) or []:
        node = _find_func_node(tree, name)
        if node is None:
            return {"ok": False, "reason": f"function {name!r} not found"}
        seg = ast.get_source_segment(src, node)
        if seg is None:
            return {"ok": False, "reason": f"could not extract source for {name!r}"}
        try:
            exec(seg, ns)
        except Exception as e:
            return {"ok": False, "reason": f"exec {name!r} failed: {type(e).__name__}: {e}"}

    for a in asserts:
        expr = a["expr"]
        setup = a.get("setup")
        if setup is not None:
            try:
                exec(setup, ns)
            except Exception as e:
                return {"ok": False, "reason": f"setup error for {expr}: {type(e).__name__}: {e}"}
        try:
            ok = eval(expr, ns)
        except Exception as e:
            return {"ok": False, "reason": f"assert error: {expr}: {type(e).__name__}: {e}"}
        if not ok:
            return {"ok": False, "reason": f"assert failed: {expr}"}

    return {"ok": True}

print(json.dumps(_run(json.loads(sys.argv[1]))))
'''


@register("exec_assert")
def check(tools, texts, chk):
    root = Path(chk.get("_project_dir", ""))
    target = root / chk["path"]
    timeout = int(chk.get("timeout", 5))

    config = {
        "path": str(target),
        "constants": chk.get("constants", []),
        "functions": chk.get("functions", []),
        "imports": chk.get("imports", []),
        "asserts": chk.get("asserts", []),
    }

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _HARNESS, json.dumps(config)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"exec_assert timeout after {timeout}s"
    except FileNotFoundError:
        return False, f"exec_assert: python interpreter not found ({sys.executable!r})"

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()[:400]
        return False, f"exec_assert harness crashed (rc={proc.returncode}): {stderr}"

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return False, "exec_assert harness produced no output"

    last_line = stdout.splitlines()[-1]
    try:
        result = json.loads(last_line)
    except json.JSONDecodeError as e:
        return False, f"exec_assert harness produced invalid output: {last_line[:200]!r} ({e})"

    if result.get("ok"):
        return True, None
    return False, result.get("reason", "assert failed (no reason)")
