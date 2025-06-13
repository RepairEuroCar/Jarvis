import doctest
import importlib
import pkgutil
import jarvis


def test_docstrings():
    failures = 0
    for mod in pkgutil.walk_packages(jarvis.__path__, jarvis.__name__ + "."):
        try:
            module = importlib.import_module(mod.name)
        except Exception:
            continue
        doc = getattr(module, "__doc__", None)
        if not doc or ">>>" not in doc:
            continue
        result = doctest.testmod(module, verbose=False)
        failures += result.failed
    assert failures == 0
