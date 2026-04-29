"""
Evaluator registry. Each check type is a function:

    def check(tools, texts, chk) -> (bool, str | None)

Evaluators auto-register by being imported from subpackages.

Path-resolution contract for ``chk["_project_dir"]``:

    Evaluators may receive a relative ``_project_dir`` from any caller.
    ``eval.py`` resolves ``run_dir`` to absolute before invoking checks, so
    in the canonical path ``_project_dir`` is already absolute. Evaluators
    that spawn subprocesses with ``cwd=`` must still resolve any path
    arguments they pass to those subprocesses to absolute themselves --
    relative-path interactions across ``cwd`` boundaries cause silent path
    doubling (the subprocess re-resolves the relative argv path against
    its new cwd). See ``evaluators/content/exec_function.py`` for the
    canonical pattern: ``(project_dir / rel).resolve()`` before any
    cwd-changing subprocess call.
"""

_registry: dict[str, callable] = {}


def register(name):
    def decorator(fn):
        _registry[name] = fn
        return fn
    return decorator


def get(name):
    return _registry.get(name)
