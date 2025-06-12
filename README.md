# Jarvis

This project is a simple voice assistant prototype. To start the assistant run:

```bash
python main.py
```

Ensure required dependencies are installed using `requirements.txt`.

## Additional commands

- `self_learn <trainer_id>` – trains or fine-tunes a model through the Seq2SeqTrainer module.
- `self_update commit <message>` – stages all changes and commits them with the provided message.
- `self_update pull [remote branch]` – pulls updates from a remote repository.

**Caution**: these commands execute heavy ML training and Git operations. Use them only if you understand the consequences and have configured the trainer and repository paths correctly.
