from __future__ import annotations

import time
from typing import Any, Literal

from .composer import compose_rag_context
from .config import RagSettings, load_rag_settings
from .embeddings import EmbeddingClient
from .retriever import search
from .store import index_ready, load_index

_service: "RagService | None" = None


class RagService:
    def __init__(self, settings: RagSettings) -> None:
        self.settings = settings
        self._records = None
        self._vectors = None
        self._embedder: EmbeddingClient | None = None

    @property
    def ready(self) -> bool:
        return index_ready(self.settings.index_dir)

    def _ensure_index(self) -> None:
        if self._records is None or self._vectors is None:
            self._records, self._vectors = load_index(self.settings.index_dir)

    def preload(self) -> None:
        """Load index into memory (call at startup)."""
        if self.ready:
            self._ensure_index()

    def _embedder_client(self) -> EmbeddingClient:
        if self._embedder is None:
            self._embedder = EmbeddingClient(self.settings)
        return self._embedder

    def retrieve(
        self,
        user_text: str,
        *,
        locale: Literal["fa", "en"] = "fa",
    ) -> tuple[str, dict[str, Any]]:
        started = time.perf_counter()
        meta: dict[str, Any] = {
            "enabled": True,
            "ready": self.ready,
            "hitCount": 0,
            "categories": [],
            "scores": [],
            "latencyMs": 0,
        }
        if not self.ready:
            meta["error"] = "index_missing"
            return "", meta

        self._ensure_index()
        assert self._records is not None and self._vectors is not None

        query = user_text.strip()
        vector = self._embedder_client().embed_query(query)
        hits = search(
            vector,
            self._records,
            self._vectors,
            top_k=self.settings.top_k,
            min_score=self.settings.min_score,
        )
        context = compose_rag_context(hits, locale=locale)
        meta["hitCount"] = len(hits)
        meta["categories"] = [h.record.category for h in hits]
        meta["scores"] = [round(h.score, 4) for h in hits]
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        return context, meta


def get_rag_service() -> RagService:
    global _service
    if _service is None:
        _service = RagService(load_rag_settings())
    return _service
