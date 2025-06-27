# Modules and fallbacks

Jarvis loads optional functionality as separate modules. Each module exposes a
`setup(jarvis, config)` coroutine and may define other helpers.

## Dynamic Scaler

The `dynamic_scaler` module monitors system CPU and memory usage. When the
configured thresholds are exceeded it pauses low priority modules using
`ModuleManager.pause_module`. Once utilization drops, previously paused modules
are resumed.

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

## Resource monitoring

Long-running modules that maintain background threads or spawn subprocesses
should expose a ``get_pid()`` method returning the operating system process
ID. :class:`modules.resource_limiter.ResourceLimiter` relies on this method to
track CPU and memory usage. Modules running entirely in the main process can
simply ``return os.getpid()``.
