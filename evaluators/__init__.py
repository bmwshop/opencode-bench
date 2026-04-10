"""
Evaluator registry. Each check type is a function:

    def check(tools, texts, chk) -> (bool, str | None)

Evaluators auto-register by being imported from subpackages.
"""

_registry: dict[str, callable] = {}


def register(name):
    def decorator(fn):
        _registry[name] = fn
        return fn
    return decorator


def get(name):
    return _registry.get(name)
