# Jarvis

This project is a simple voice assistant prototype. To start the assistant run:

```bash
python main.py
```

Ensure required dependencies are installed using `requirements.txt`.

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

To inspect the full JSON schema of available settings, run:

```bash
python -m jarvis.core.main --schema
```

## Additional commands

- `self_learn <trainer_id>` – trains or fine-tunes a model through the Seq2SeqTrainer module.
- `self_update commit <message>` – stages all changes and commits them with the provided message.
- `self_update pull [remote branch]` – pulls updates from a remote repository.
- `repl` – opens an interactive Python session with Jarvis loaded.

**Caution**: these commands execute heavy ML training and Git operations. Use them only if you understand the consequences and have configured the trainer and repository paths correctly.

### Code formatting

Run the formatting tools with:

```bash
./scripts/format.sh
```

Use `--check` to verify formatting in CI or before committing changes.

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
