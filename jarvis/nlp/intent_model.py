from pathlib import Path
from typing import Any

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - optional dependency
    pipeline = None


class IntentModel:
    """Wrapper around a HuggingFace text-classification pipeline."""

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        if pipeline is not None:
            try:
                self._clf = pipeline("text-classification", model=model_path)
            except Exception:  # pragma: no cover - loading errors
                self._clf = None
        else:  # pragma: no cover - transformers missing
            self._clf = None

    def predict(self, text: str, context : None | [list[str]] = None) -> dict[str, Any]:
        if self._clf is None:
            raise RuntimeError("IntentModel requires the transformers package")

        combined = text
        if context:
            combined = " ".join(context[-3:]) + " " + text
        result = self._clf(combined)[0]
        return {
            "intent": result.get("label", ""),
            "confidence": float(result.get("score", 0.0)),
        }

    def update_model(self, text: str, intent: str) -> None:
        """Fine-tune the underlying model with an additional example."""
        if self._clf is None:
            raise RuntimeError("IntentModel requires the transformers package")

        try:
            import torch
            from torch.utils.data import Dataset
            from transformers import Trainer, TrainingArguments
        except Exception:  # pragma: no cover - optional dependency
            return

        tokenizer = self._clf.tokenizer
        model = self._clf.model

        label2id = model.config.label2id or {}
        if intent not in label2id:
            new_id = max(label2id.values(), default=-1) + 1
            label2id[intent] = new_id
            model.config.label2id = label2id
            model.config.id2label = {i: l for l, i in label2id.items()}

        enc = tokenizer([text], padding=True, truncation=True)

        class _SingleDataset(Dataset):
            def __len__(self) -> int:
                return 1

            def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:  # type: ignore[name-defined]
                item = {k: torch.tensor(v[idx]) for k, v in enc.items()}
                item["labels"] = torch.tensor(label2id[intent])
                return item

        train_ds = _SingleDataset()

        args = TrainingArguments(
            output_dir=str(Path(self.model_path).with_suffix("_ft")),
            num_train_epochs=1,
            per_device_train_batch_size=1,
            learning_rate=5e-5,
            logging_steps=1,
            report_to=[],
        )

        trainer = Trainer(model=model, args=args, train_dataset=train_ds)
        trainer.train()
        trainer.save_model(self.model_path)
        self._clf = pipeline("text-classification", model=self.model_path)
