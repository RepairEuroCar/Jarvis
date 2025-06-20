from typing import Any, Dict, List, Optional

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

    def predict(self, text: str, context: Optional[List[str]] = None) -> Dict[str, Any]:
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
