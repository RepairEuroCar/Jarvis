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

**Caution**: these commands execute heavy ML training and Git operations. Use them only if you understand the consequences and have configured the trainer and repository paths correctly.
