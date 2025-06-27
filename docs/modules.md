# Modules and fallbacks

Jarvis loads optional functionality as separate modules. Each module exposes a
`setup(jarvis, config)` coroutine and may define other helpers.

## Module configuration

The `ModuleManager` reads configuration from `config/config.yaml`. Each module
section accepts a `requirements` list containing pip-style package specifiers.
They must be importable before the module starts.

```yaml
modules:
  git_manager:
    requirements:
      - gitpython>=3.1
```

## Declaring `REQUIRES`

Modules can also declare their dependencies directly in code. Define a
`REQUIRES` list at the top level and the manager will merge it with the config.

```python
# modules/git_manager.py
REQUIRES = ["gitpython>=3.1"]
```

## Registering fallbacks

`FallbackManager` manages alternative callables when a command fails. Register a
fallback by key:

```python
from jarvis.core.fallback_manager import fallback_manager

async def offline_repo_status():
    return "cannot reach remote"

fallback_manager.register("git.status", offline_repo_status)
```

Calling `fallback_manager.run("git.status")` tries the main handler first and
runs the fallback on error. Remove the handler with
`fallback_manager.unregister("git.status")`.
