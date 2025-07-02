"""Named entity recognition utilities."""

from typing import Any

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency
    spacy = None  # type: ignore

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - optional dependency
    pipeline = None


class NERModel:
    """Wrapper around spaCy or HuggingFace transformers for NER."""

    def __init__(self, model_name : None | [str] = None) -> None:
        self.model_name = model_name or "en_core_web_sm"
        self._model: Any = None
        self._is_spacy = False
        if spacy is not None:
            try:
                self._model = spacy.load(self.model_name)
                self._is_spacy = True
            except Exception:  # pragma: no cover - loading errors
                self._model = None
        if self._model is None and pipeline is not None:
            try:
                self._model = pipeline(
                    "ner",
                    model=self.model_name,
                    grouped_entities=True,
                )
                self._is_spacy = False
            except Exception:  # pragma: no cover - loading errors
                self._model = None

    def extract_entities(self, text: str) -> list[dict[str, str]]:
        """Return a list of entity dicts with ``text`` and ``label`` keys."""
        if self._model is None:
            raise RuntimeError("NERModel requires spaCy or transformers package")

        if self._is_spacy:
            doc = self._model(text)
            return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

        results = self._model(text)
        return [
            {"text": ent.get("word", ""), "label": ent.get("entity_group", "")}
            for ent in results
        ]
