"""
exec_function: run a student-authored Python script against an AST-extracted,
side-effect-free stub of a target module.

Build stages (all inside an isolated subprocess):
  1. Read + parse `chk["source"]`. Copy every top-level literal Assign /
     AnnAssign into the stub. Copy each function named in
     `chk["functions"]` via `ast.get_source_segment`. Prepend `import M` for
     each module in `chk["imports"]`.
  2. Write the stub to `tempdir/{Path(source).stem}.py`. Also write a
     `_runner.py` to `tempdir` whose job is to prepend its own directory to
     `sys.path` and then `exec()` the student's script. This guarantees the
     stub shadows the real source (otherwise Python would make the student
     script's own directory — the project dir containing the real source —
     the first entry on `sys.path`).
  3. Run `python <tempdir>/_runner.py <script_abs>` with `cwd = project_dir`
     and `PYTHONPATH = tempdir:<existing PYTHONPATH>`. The student's import
     of the target module resolves to the stub. The script still sees
     `__file__ = <script_abs>`, `__name__ = '__main__'`, and the correct
     `cwd`, so normal script semantics are preserved.

Pass condition: subprocess exits 0 AND stdout contains every needle listed
in `chk["expect_stdout_contains"]` (accepted as `str` or `list[str]`). On
fail, the reason surfaces either the last non-empty stderr line
(truncated), the timeout marker, or the missing needle.

Harness-level failures (source file missing / unreadable, SyntaxError in
source, listed function not found) report as a failed check with an
explicit reason — they indicate either a damaged fixture or an eval-time
misconfiguration and should be triaged separately from model failures.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from evaluators import register


_BUILD_STUB = r'''
import ast, json, sys

def _find_func_node(tree, name):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None

def _is_literal(node):
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, SyntaxError):
        return False

def _build(config):
    source = config["source"]
    try:
        with open(source, "r") as f:
            src = f.read()
    except FileNotFoundError:
        return {"ok": False, "reason": f"source file not found: {source}"}
    except OSError as e:
        return {"ok": False, "reason": f"could not read {source}: {e}"}

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"ok": False, "reason": f"SyntaxError in {source} at line {e.lineno}: {e.msg}"}

    parts = []

    for mod_name in config.get("imports", []) or []:
        parts.append(f"import {mod_name}")

    for node in tree.body:
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                continue
            tgt = node.targets[0]
            if not isinstance(tgt, ast.Name):
                continue
            if node.value is None or not _is_literal(node.value):
                continue
            seg = ast.get_source_segment(src, node)
            if seg is not None:
                parts.append(seg)
        elif isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name):
                continue
            if node.value is None or not _is_literal(node.value):
                continue
            seg = ast.get_source_segment(src, node)
            if seg is not None:
                parts.append(seg)

    for name in config.get("functions", []) or []:
        node = _find_func_node(tree, name)
        if node is None:
            return {"ok": False, "reason": f"function {name!r} not found in {source}"}
        seg = ast.get_source_segment(src, node)
        if seg is None:
            return {"ok": False, "reason": f"could not extract source for function {name!r}"}
        parts.append(seg)

    stub = "\n\n".join(parts) + "\n"
    return {"ok": True, "stub": stub}

print(json.dumps(_build(json.loads(sys.argv[1]))))
'''


def _needles(chk):
    raw = chk.get("expect_stdout_contains")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return [str(raw)]


@register("exec_function")
def check(tools, texts, chk):
    project_dir = Path(chk.get("_project_dir", ""))
    source_rel = chk["source"]
    script_rel = chk["script"]
    functions = chk.get("functions", []) or []
    imports = chk.get("imports", []) or []
    timeout = int(chk.get("timeout", 10))
    needles = _needles(chk)

    source_path = (project_dir / source_rel).resolve()
    script_path = (project_dir / script_rel).resolve()

    if not script_path.exists():
        return False, f"script not found: {script_rel}"

    build_config = {
        "source": str(source_path),
        "functions": list(functions),
        "imports": list(imports),
    }
    try:
        build_proc = subprocess.run(
            [sys.executable, "-c", _BUILD_STUB, json.dumps(build_config)],
            capture_output=True,
            text=True,
            timeout=max(5, timeout),
        )
    except subprocess.TimeoutExpired:
        return False, f"exec_function stub build timeout after {max(5, timeout)}s"
    except FileNotFoundError:
        return False, f"exec_function: python interpreter not found ({sys.executable!r})"

    if build_proc.returncode != 0:
        stderr = (build_proc.stderr or "").strip()[:400]
        return False, f"exec_function stub build crashed (rc={build_proc.returncode}): {stderr}"

    stdout_lines = (build_proc.stdout or "").strip().splitlines()
    if not stdout_lines:
        return False, "exec_function stub build produced no output"
    try:
        build_result = json.loads(stdout_lines[-1])
    except json.JSONDecodeError as e:
        return False, f"exec_function stub build produced invalid output: {stdout_lines[-1][:200]!r} ({e})"

    if not build_result.get("ok"):
        return False, build_result.get("reason", "stub build failed")

    stub_code = build_result["stub"]

    with tempfile.TemporaryDirectory(prefix="exec_function_") as td:
        stub_dir = Path(td)
        # Mirror the source's relative path inside the stub dir so a nested
        # package import (e.g. `from httpx._utils import ...` for source
        # `httpx/_utils.py`) resolves correctly through PYTHONPATH. For a
        # flat source path like `train.py` this is equivalent to the old
        # behaviour of writing one file at the stub-dir root. We materialize
        # empty `__init__.py` files for every parent directory so Python
        # treats the chain as a proper package tree.
        target_in_stub = stub_dir / source_rel
        target_in_stub.parent.mkdir(parents=True, exist_ok=True)
        target_in_stub.write_text(stub_code)
        parent = target_in_stub.parent
        while parent != stub_dir and stub_dir in parent.parents:
            init_path = parent / "__init__.py"
            if not init_path.exists():
                init_path.write_text("")
            parent = parent.parent

        runner_code = (
            "import sys, os\n"
            "_here = os.path.dirname(os.path.abspath(__file__))\n"
            "sys.path.insert(0, _here)\n"
            "_target = sys.argv[1]\n"
            "sys.argv = [_target]\n"
            "with open(_target, 'r') as _f:\n"
            "    _src = _f.read()\n"
            "_code = compile(_src, _target, 'exec')\n"
            "_globals = {'__name__': '__main__', '__file__': _target, '__builtins__': __builtins__}\n"
            "exec(_code, _globals)\n"
        )
        runner_path = stub_dir / "_runner.py"
        runner_path.write_text(runner_code)

        env = os.environ.copy()
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{stub_dir}{os.pathsep}{existing_pp}" if existing_pp else str(stub_dir)
        )

        try:
            run_proc = subprocess.run(
                [sys.executable, str(runner_path), str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(project_dir).resolve()),
                env=env,
            )
        except subprocess.TimeoutExpired:
            return False, f"exec_function script timeout after {timeout}s"
        except FileNotFoundError:
            return False, f"exec_function: python interpreter not found ({sys.executable!r})"

        if run_proc.returncode != 0:
            stderr = (run_proc.stderr or "").strip()
            last = ""
            for line in reversed(stderr.splitlines()):
                line = line.strip()
                if line:
                    last = line
                    break
            detail = last[:200] if last else "(no stderr)"
            return False, f"exec_function script exit {run_proc.returncode}: {detail}"

        stdout = run_proc.stdout or ""
        for needle in needles:
            if needle not in stdout:
                return False, f"exec_function stdout missing {needle!r}"

        return True, None
