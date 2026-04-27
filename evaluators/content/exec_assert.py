"""
exec_assert: run a list of Python assertion expressions against symbols
AST-extracted from one or more target source files.

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

Two input shapes are supported:

    Single-file (legacy)
    --------------------
    {"type": "exec_assert",
     "path": "src/foo.py",
     "functions": ["bar"],
     "constants": ["BAZ"],
     "imports": ["math"],
     "asserts": [{"expr": "bar(1) == 2"}]}

    Multi-file
    ----------
    {"type": "exec_assert",
     "targets": [
         {"path": "src/a.py", "functions": ["impl"], "constants": [], "imports": []},
         {"path": "src/b.py", "functions": ["caller"], "constants": [], "imports": []}
     ],
     "asserts": [{"expr": "caller() and impl(1) == 2"}]}

In the multi-file form all targets are AST-extracted into the same
namespace before any assert runs; symbol collisions across targets are
rejected up front so the order of `targets` cannot silently shadow an
implementation. The `asserts` list runs exactly once over the unified
namespace.
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
    """Find a top-level FunctionDef OR ClassDef by name.

    Class names are accepted so callers can list a class in `functions`
    to bind the whole class (with its methods) into the namespace. The
    asserts can then instantiate the class and exercise its methods.
    Method-by-qualified-name (Class.method) is intentionally not
    supported: use the bare class name and write asserts that
    construct an instance and call the method.
    """
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return node
    return None

def _load_target(target, ns):
    """Load constants/imports/functions from one target file into ns.

    Returns either None (success) or a {"ok": False, ...} dict on failure.
    """
    path = target["path"]
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
        return {"ok": False, "reason": f"SyntaxError in {path} at line {e.lineno}: {e.msg}"}

    for name in target.get("constants", []) or []:
        value_node = _find_const_value(tree, name)
        if value_node is None:
            return {"ok": False, "reason": f"constant {name!r} not found in {path}"}
        try:
            ns[name] = ast.literal_eval(value_node)
        except (ValueError, SyntaxError) as e:
            return {"ok": False, "reason": f"constant {name!r} in {path} not a literal: {e}"}

    for mod_spec in target.get("imports", []) or []:
        # Two forms supported:
        #   "json"                    -> ns["json"] = json (bare-module form, legacy)
        #   "collections:OrderedDict" -> ns["OrderedDict"] = collections.OrderedDict
        #   "abc:Mapping,Set"         -> ns["Mapping"], ns["Set"] = ...
        if ":" in mod_spec:
            mod_name, names_part = mod_spec.split(":", 1)
            mod_name = mod_name.strip()
            wanted = [n.strip() for n in names_part.split(",") if n.strip()]
            if not wanted:
                return {"ok": False, "reason": f"import spec {mod_spec!r} has empty name list"}
            try:
                mod = __import__(mod_name, fromlist=wanted)
            except ImportError as e:
                return {"ok": False, "reason": f"import {mod_name!r} failed: {e}"}
            for name in wanted:
                if not hasattr(mod, name):
                    return {
                        "ok": False,
                        "reason": f"from {mod_name} import {name}: name not found on module",
                    }
                ns[name] = getattr(mod, name)
        else:
            try:
                ns[mod_spec] = __import__(mod_spec)
            except ImportError as e:
                return {"ok": False, "reason": f"import {mod_spec!r} failed: {e}"}

    for name in target.get("functions", []) or []:
        node = _find_func_node(tree, name)
        if node is None:
            return {"ok": False, "reason": f"function {name!r} not found in {path}"}
        # Strip in-body relative imports (`from .x import y`). These are
        # functionally correct in the real package but fail when the
        # function is extracted into a bare namespace with no parent
        # package -- the imported names are already in `ns` via the
        # other target's extraction. Iterate over a copy because we
        # mutate the underlying body lists.
        def _strip_relative_imports(n):
            for attr in ("body", "orelse", "finalbody", "handlers"):
                if hasattr(n, attr):
                    items = getattr(n, attr)
                    if isinstance(items, list):
                        items[:] = [
                            x for x in items
                            if not (isinstance(x, ast.ImportFrom) and (x.level or 0) > 0)
                        ]
                        for child in items:
                            _strip_relative_imports(child)
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            _strip_relative_imports(node)
        try:
            seg = ast.unparse(node)
        except Exception:
            seg = ast.get_source_segment(src, node)
        if seg is None:
            return {"ok": False, "reason": f"could not extract source for {name!r} in {path}"}
        try:
            exec(seg, ns)
        except Exception as e:
            return {"ok": False, "reason": f"exec {name!r} from {path} failed: {type(e).__name__}: {e}"}

    return None


def _run(config):
    asserts = config.get("asserts", []) or []
    targets = config.get("targets")
    if targets is None:
        # legacy single-file form: synthesize a one-element targets list.
        targets = [{
            "path": config["path"],
            "functions": config.get("functions", []) or [],
            "constants": config.get("constants", []) or [],
            "imports": config.get("imports", []) or [],
        }]

    if not targets:
        return {"ok": False, "reason": "no targets supplied"}

    # Pre-flight: reject symbol collisions so target order never matters.
    seen = {}
    for t in targets:
        for kind in ("functions", "constants"):
            for name in t.get(kind, []) or []:
                prior = seen.get(name)
                if prior is not None and prior != t["path"]:
                    return {"ok": False, "reason": (
                        f"symbol {name!r} declared in both {prior!r} and {t['path']!r}; "
                        f"resolve the collision in the manifest"
                    )}
                seen[name] = t["path"]

    # Prepopulate dunder names that legitimate Python may reference at
    # module/function scope (e.g. annotation evaluation can hit __name__,
    # and some helpers gate behaviour on `if __name__ == '__main__':`).
    # Without this, exec() inherits a bare globals dict that omits these
    # builtins-equivalent names and the harness rejects otherwise-valid
    # model edits with `KeyError: '__name__' not in globals`.
    ns = {
        "__name__": "__opencode_bench_exec_assert__",
        "__doc__": None,
        "__package__": None,
        "__loader__": None,
        "__spec__": None,
        "__builtins__": __builtins__,
    }
    for t in targets:
        err = _load_target(t, ns)
        if err is not None:
            return err

    # Collect ALL failures rather than short-circuit on the first one. This
    # lets failure-mode analysis distinguish "no-change" from "partial-edit"
    # within a single trial: when the model's edit is partially correct the
    # later asserts (often `partial-edit`-misstep classified) would not fire
    # if we returned on the first `no-change` mismatch.
    failures = []
    for a in asserts:
        expr = a["expr"]
        setup = a.get("setup")
        if setup is not None:
            try:
                exec(setup, ns)
            except Exception as e:
                failures.append(f"setup error for {expr}: {type(e).__name__}: {e}")
                continue
        try:
            ok = eval(expr, ns)
        except Exception as e:
            failures.append(f"assert error: {expr}: {type(e).__name__}: {e}")
            continue
        if not ok:
            failures.append(f"assert failed: {expr}")

    if failures:
        return {"ok": False, "reason": " | ".join(failures)}
    return {"ok": True}

print(json.dumps(_run(json.loads(sys.argv[1]))))
'''


@register("exec_assert")
def check(tools, texts, chk):
    root = Path(chk.get("_project_dir", ""))
    timeout = int(chk.get("timeout", 5))

    if chk.get("targets"):
        # Multi-file form: rebase every target path under the project dir.
        rebased = []
        for t in chk["targets"]:
            rebased.append({
                "path": str(root / t["path"]),
                "constants": t.get("constants", []) or [],
                "functions": t.get("functions", []) or [],
                "imports": t.get("imports", []) or [],
            })
        config = {
            "targets": rebased,
            "asserts": chk.get("asserts", []),
        }
    else:
        target = root / chk["path"]
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
