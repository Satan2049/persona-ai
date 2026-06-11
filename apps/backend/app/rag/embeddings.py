from typing import Sequence

import httpx

from .config import RagSettings


class EmbeddingClient:
    def __init__(self, settings: RagSettings) -> None:
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        key = self._settings.embedding_api_key
        if not key:
            raise RuntimeError(
                "EMBEDDING_API_KEY is not set. Add it to backend/.env before building or querying the index."
            )
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        base = self._settings.embedding_api_base
        if not base:
            raise RuntimeError("EMBEDDING_API_BASE is not set in backend/.env")
        url = f"{base.rstrip('/')}/embeddings"
        payload = {
            "model": self._settings.embedding_model,
            "input": list(texts),
        }
        with httpx.Client(timeout=self._settings.embedding_timeout_seconds) as client:
            response = client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            body = response.json()
        rows = body.get("data") or []
        if len(rows) != len(texts):
            raise RuntimeError(
                f"Embedding API returned {len(rows)} vectors for {len(texts)} inputs"
            )
        ordered = sorted(rows, key=lambda r: int(r.get("index", 0)))
        return [list(row["embedding"]) for row in ordered]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
