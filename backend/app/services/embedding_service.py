"""Embedding providers used by semantic search and case indexing."""

from __future__ import annotations

from typing import Any, Iterable

from app.config.settings import settings


def generate_case_embedding_text(case: Any) -> str:
    """Build deterministic embedding text from structured legal case data."""
    if isinstance(case, str):
        return case.strip()

    def value(*names: str) -> str:
        for name in names:
            item = case.get(name) if isinstance(case, dict) else getattr(case, name, None)
            if item is not None and item != "":
                if isinstance(item, (list, tuple, set)):
                    return "; ".join(str(part) for part in item)
                if isinstance(item, dict):
                    return "; ".join(f"{key}: {item[key]}" for key in sorted(item))
                return str(item)
        return ""

    sections = [
        ("CASE TITLE", value("case_title", "title", "case_name")),
        ("COURT", value("court", "court_name", "court_level")),
        ("CASE NUMBER", value("case_number", "number")),
        ("PARTIES", value("parties", "plaintiff", "defendant", "petitioner", "respondent")),
        ("LEGAL PROVISIONS", value("legal_provisions", "provisions", "sections", "cited_sections")),
        ("LEGAL ISSUES", value("legal_issues", "issues", "key_issues")),
        ("ARGUMENTS", value("claims_arguments", "arguments", "claims")),
        ("PRECEDENTS", value("cited_precedents", "precedents", "citations")),
        ("DECISION", value("decision", "disposition", "outcome")),
        ("TIMELINE", value("timeline", "events")),
    ]
    return "\n\n".join(f"{label}:\n{text}" for label, text in sections if text).strip()


class EmbeddingService:
    """Lazily loaded local embeddings with an optional Gemini provider."""

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower().strip()
        self.model_name = settings.EMBEDDING_MODEL
        self._model = None
        self._dimension = None

    def _load_local_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "Local embeddings are unavailable. Install sentence-transformers."
                ) from error
            self._model = SentenceTransformer(self.model_name)
            get_dimension = getattr(
                self._model,
                "get_embedding_dimension",
                self._model.get_sentence_embedding_dimension,
            )
            self._dimension = int(get_dimension())
        return self._model

    def generate_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            return []
        if self.provider == "local":
            model = self._load_local_model()
            vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=False)
            return [float(value) for value in vector.tolist()]
        if self.provider == "gemini":
            from app.services.google_api_service import GoogleAPIClient

            return GoogleAPIClient().generate_embedding(text)
        raise RuntimeError(f"Unsupported embedding provider: {self.provider}")

    def generate_embeddings(self, texts: Iterable[str]) -> list[list[float]]:
        values = [text for text in texts]
        if not values:
            return []
        if self.provider == "local":
            model = self._load_local_model()
            vectors = model.encode(values, convert_to_numpy=True, normalize_embeddings=False)
            return [[float(value) for value in vector.tolist()] for vector in vectors]
        return [self.generate_embedding(text) for text in values]

    @property
    def dimension(self) -> int | None:
        if self._dimension is not None:
            return self._dimension
        if self.provider == "local":
            self._load_local_model()
        return self._dimension


embedding_service = EmbeddingService()
