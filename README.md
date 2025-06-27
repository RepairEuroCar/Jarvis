# Jarvis
[![codecov](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/OWNER/REPO)

This project is a simple voice assistant prototype. To start the assistant run:

```bash
python main.py
```

Alternatively you can launch Jarvis in autonomous voice mode using:

```bash
python scripts/autonomous.py
```

## Running the GUI

Launch the Tk interface with:
```bash
python gui.py
```

The input field supports `<Tab>` completion. Press the key while typing a
command to cycle through the available command names from `jarvis.commands`.

Install runtime dependencies with:

```bash
pip install -r requirements.txt
```

For development and testing install the additional tools from `dev-requirements.txt`:

```bash
pip install -r dev-requirements.txt
```

## Configuration

`Jarvis` reads configuration from environment variables and an optional
`config.yaml` file (see `config/config.yaml` for an example). Environment
variables should use the `JARVIS_` prefix.
Default values are:

| Variable | Default |
|----------|---------|
| `JARVIS_LOG_LEVEL` | `INFO` |
| `JARVIS_DEFAULT_USER` | `User` |
| `JARVIS_MAX_CACHE_SIZE` | `10` |
| `JARVIS_VOICE_ENABLED` | `True` |
| `JARVIS_VOICE_ACTIVATION_PHRASE` | `джарвис` |
| `JARVIS_VOICE_RATE` | `180` |
| `JARVIS_VOICE_VOLUME` | `0.9` |
| `JARVIS_PLUGIN_DIR` | `plugins` |
| `JARVIS_EXTRA_PLUGIN_DIRS` | `~/.jarvis/plugins` |
| `JARVIS_ALLOWED_NETWORKS` | `0.0.0.0/0` |

`allowed_networks` defines the CIDR ranges Jarvis modules may
connect to or scan. Leaving the default `0.0.0.0/0` allows
operations against any address, which could be unsafe in untrusted
environments. Provide a restricted list in `config/config.yaml`
to limit network commands to known networks. After modifying the file or
the `JARVIS_ALLOWED_NETWORKS` environment variable you can reload the
values at runtime by calling `kali_tools.reload_allowed_networks()`.

### Module priority

The `config.yaml` file supports an optional `autoload_modules` section used to
load features automatically. Each entry specifies a module name and its
configuration:

```yaml
autoload_modules:
  analyzer:
    enabled: true
    priority: 10
  git_manager:
    enabled: true
    priority: 20
```

Modules with a **lower** `priority` number load before those with higher values.
The snippet above enables two core modules shipped with Jarvis. Add more entries
as needed to control startup order.

### Logging

Logging is initialised by calling `utils.logger.setup_logging()` which is
invoked by the core on startup. The log level defaults to the value of the
`JARVIS_LOG_LEVEL` environment variable. You can adjust verbosity in your own
scripts:

```python
import logging
from utils.logger import setup_logging

setup_logging(level=logging.DEBUG)
```

## Security tool wrappers

Jarvis exposes asynchronous helpers for several security utilities through
`modules/kali_tools.py`.

| Tool | Purpose | Comments |
|------|---------|----------|
| `nmap` | Network scanning and host discovery | Respects `allowed_networks` |
| `hydra` | Credential bruteforce for many services | `bruteforce_ssh` wraps SSH |
| `sqlmap` | Automated SQL injection testing | |
| `msfconsole` | Launch the Metasploit console | Optional resource script |
| `burpsuite` | Web vulnerability testing | |
| `aircrack-ng` | Crack captured Wi-Fi handshakes | |
| `wireshark` | Inspect packet captures | |
| `john` | Password hash cracking | new wrapper |
| `hashcat` | GPU-accelerated hash cracking | new wrapper |
| `crunch` | Generate custom wordlists | new wrapper |
| `yara` | Scan files with YARA rules | new wrapper |
| `volatility` | Memory forensics | new wrapper |
| `mitmproxy` | Intercept HTTP/S traffic | new wrapper |

The newest additions include wrappers for `john`, `hashcat`, `crunch`, `yara`,
`volatility` and `mitmproxy`. These helpers assume the underlying binaries are
installed. `yara` enables signature-based heuristics scanning, `volatility`
provides memory dump analysis and `mitmproxy` lets you intercept traffic for
training or inspection.

```python
await kali_tools.run_yara("rules.yar", "suspect.bin")
await kali_tools.run_volatility("mem.img", "pslist")
await kali_tools.run_mitmproxy("-p 8080")
```

To inspect the full JSON schema of available settings, run:

```bash
python -m jarvis.core.main --schema
```


## Additional commands

- `self_learn <trainer_id>` – trains or fine-tunes a model through the Seq2SeqTrainer module.
- `self_update commit <message> [remote branch]` – stages all changes, commits with the message and pushes if a remote/branch is specified.
- `self_update pull [remote branch]` – pulls updates from the given remote and branch (defaults to `origin main`).
- `check_updates [remote] [branch]` – shows the latest commit on the remote if it differs from the local one.
- `repl` – opens an interactive Python session with Jarvis loaded.
- `explain_solution [n]` – prints how the last task was solved. Pass a number to show several recent solutions.

Example:

```bash
explain_solution 2
```

**Caution**: these commands execute heavy ML training and Git operations. Use them only if you understand the consequences and have configured the trainer and repository paths correctly.

## Command dispatcher

Jarvis includes a lightweight command dispatcher that lets modules expose
additional CLI actions. Commands are written in the form
`<module>.<action> [--key=value|--flag|-k value]` and are resolved at runtime.

Use `list_commands` to print every registered command or `help <module> <action>`
to display the handler's documentation. The dispatcher prints a short usage
message when no command is specified:

```text
Enter <module> <action> [--param=value|--flag|-k value]...
```

Modules expose a ``register_commands(dispatcher)`` function that installs their
handlers. This avoids side effects when importing the module. Example:

```python
from command_dispatcher import default_dispatcher
from modules import ml_trainer, git_manager

ml_trainer.register_commands(default_dispatcher)
git_manager.register_commands(default_dispatcher)
```

### Examples

- `ml.train --config=training.json`
- `ml.evaluate --config=eval.json --checkpoint=model.pt`
- `git.commit -m "Initial commit" --repo=project --sign`
- `git.push --remote=origin --branch=main -f`

### Built-in commands

The dispatcher itself exposes a few built-in utilities. Their parameters are
validated using small Pydantic models:

| Command | Parameters | Description |
|---------|------------|-------------|
| `list_commands` | *(none)* | Show all registered commands |
| `help` | `--command=<module action>` | Display handler documentation |
| `exit` | *(none)* | Return the `CommandDispatcher.EXIT` sentinel |
| `load` | `--module=<name>` | Load a Jarvis module |
| `unload` | `--module=<name>` | Unload a Jarvis module |
| `reload` | `--module=<name>` | Reload a Jarvis module |

Use `load`, `unload` and `reload` to manage optional features without
restarting the assistant.

## REST API

Run the lightweight REST service to control Jarvis programmatically:

```bash
python -m jarvis.rest_api
```

Send a command via HTTP POST:

```bash
curl -X POST -H 'Content-Type: application/json' \
     -d '{"text": "help"}' http://localhost:8001/command
```

The service exposes `/command` and `/status` endpoints for issuing commands and
querying the current state.

### Code formatting

Run the formatting tools with:

```bash
./scripts/format.sh
```

`flake8` reads its configuration from `pyproject.toml` via the
`flake8-pyproject` plugin installed with the tools from `dev-requirements.txt`.

Use `--check` to verify formatting in CI or before committing changes.

## Optional features

Jarvis can leverage Redis for caching and Docker for project initialization.
Install the optional packages if you plan to use these capabilities:

```bash
pip install aioredis docker
```

Some wrappers require extra security tools. Install `yara`, `volatility` and
`mitmproxy` if you intend to use their helpers.
### PostgreSQL support


An optional module allows Jarvis to use a PostgreSQL database. The `postgres_interface` module executes both `docs/jarvis_users_pg.sql` and `docs/jarvis_topics_pg.sql` when loaded. Install `asyncpg` from `requirements.txt` and call `postgres_interface.load_module` to enable the `list_pg_users` command.



## Learning from mistakes

The repository includes an example script `scripts/run_with_retry.py` that
demonstrates how you can restart a Python program after fixing a `SyntaxError`.
Run it with a path to a Python file:

```bash
python scripts/run_with_retry.py your_script.py
```

If a syntax issue is detected, you'll be prompted to correct the file and try
again, illustrating a simple "learn from mistakes" workflow.

## Design patterns

The codebase utilises a couple of classic patterns:

- **Factory** – `jarvis/brain.py` defines `ThoughtProcessorFactory` which
  creates instances of different thought processors. Processors are registered
  in the factory and the `Brain` class obtains them via this facility.
- **Singleton** – `Jarvis` in `jarvis/core/main.py` implements the singleton
  pattern so repeated instantiation returns the same assistant instance.

## Automatic import inference

`write_code` can prepend common imports based on a textual description. Example:

```python
from utils.code_generator import write_code

task = {
    "dsl": "создай функцию foo",
    "path": "foo.py",
    "description": "Создай телеграм бота",
}
write_code(task)
# foo.py will start with 'import aiogram'
```

## Developing plugins

Jarvis can load additional functionality from Python modules located in the
directory defined by the `plugin_dir` setting (default: `plugins`) and any
paths listed in `extra_plugin_dirs`. By default `~/.jarvis/plugins` is also
scanned. The convention is to place modules in the top-level `plugins/` directory so they are
automatically discovered. Every module found there is imported on startup and,
if it exposes a `register(jarvis)` function, that function is called with the
running `Jarvis` instance. Use it to register new commands or initialise
background tasks.

Create a file `plugins/hello.py` with a simple command:

```python
from jarvis.core.main import RegisteredCommand, CommandInfo

def register(jarvis):
    async def hello(event):
        return "Hello from plugin!"

    jarvis.commands["hello"] = RegisteredCommand(
        info=CommandInfo(name="hello", aliases=[], description="Say hello"),
        handler=hello,
    )
```

After restarting Jarvis you can invoke the command by typing `hello`.

### Common pitfalls

- Plugin file not placed inside `plugins/` or missing the `.py` extension.
- Forgetting to define `register()` in the module.
- Import errors caused by missing dependencies.

### Troubleshooting plugin import errors

If a plugin fails to load you will see warnings such as `Failed loading plugin`
in the console output. Ensure the plugin has no syntax errors and that all
required packages are installed. When creating a package directory, include an
`__init__.py` file so the loader can detect it.

## Project generation plugin

The optional `project_generator` plugin demonstrates automatic code creation
from a technical brief. After placing `plugins/project_generator.py` in the
plugin directory Jarvis loads a new command `generate_project`:

```bash
generate_project spec.txt my_project
```

`spec.txt` should contain bullet points such as `- создай функцию foo`.
Each line becomes a Python module inside `my_project` and required imports are
added automatically.

## Code analysis

`analyze_report` runs the AdvancedCodeAnalyzer over one or more Python files.
Alongside metrics and complexity checks the analyzer now executes **pylint** and
includes any warnings in the output summary.

```bash
analyze_report src/ --format=json
```

## Generating core tests

The `scripts/generate_core_tests.py` helper scans recent commits for new
functions inside `jarvis/core` and `core`. For each detected function it runs
the built-in test generator and writes the results under `tests/generated/`.

Run it with the default range to inspect the last commit:

```bash
python scripts/generate_core_tests.py
```

Specify a different git diff range if needed:

```bash
python scripts/generate_core_tests.py HEAD~2
```
## Python and ML utilities

Jarvis provides helper commands for development tasks:
- `python.create_script --name=app --skeleton=cli` creates a basic script.
- `python.run_tests --target=path` runs tests and lint.
- `ml.create_experiment --name=exp --config=cfg.json` prepares an experiment folder.
- `codex.executor.run --path=dir` executes tests and linting via the
  **CodexExecutor** wrapper located at `codex/executor.py`.


## Python reference

For a refresher on Python basics see [docs/python_overview.md](docs/python_overview.md).

