"""Startup: build FAQ index if needed and preload vectors into memory."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from .chunking import chunk_faq_records
from .config import RagSettings, load_rag_settings
from .embeddings import EmbeddingClient
from .loader import load_faq_records
from .store import index_ready, load_index, write_index

logger = logging.getLogger(__name__)


def _faq_newer_than_index(settings: RagSettings) -> bool:
    faq = Path(settings.faq_path)
    meta = Path(settings.index_dir) / "meta.jsonl"
    if not faq.is_file():
        return False
    if not meta.is_file():
        return True
    return faq.stat().st_mtime > meta.stat().st_mtime


def build_faq_index(settings: RagSettings) -> int:
    records = load_faq_records(settings.faq_path)
    if not records:
        raise RuntimeError(f"No FAQ records in {settings.faq_path}")
    chunks = chunk_faq_records(records)
    texts = [c.embed_text for c in chunks]
    client = EmbeddingClient(settings)
    vectors = np.array(client.embed_texts(texts), dtype=np.float32)
    write_index(settings.index_dir, records, vectors)
    logger.info(
        "Built RAG index: %s records, vectors shape %s -> %s",
        len(records),
        vectors.shape,
        settings.index_dir,
    )
    return len(records)


def initialize_rag() -> dict[str, Any]:
    """Called once at backend startup (sync, run via asyncio.to_thread)."""
    settings = load_rag_settings()
    status: dict[str, Any] = {
        "enabled": settings.enabled,
        "indexReady": index_ready(settings.index_dir),
        "faqPath": settings.faq_path,
        "indexDir": settings.index_dir,
        "embeddingConfigured": bool(
            settings.embedding_api_base and settings.embedding_api_key
        ),
        "recordCount": 0,
        "built": False,
        "preloaded": False,
    }

    if not settings.enabled:
        status["note"] = "RAG_ENABLED is false"
        return status

    if os.path.isfile(settings.faq_path):
        status["recordCount"] = len(load_faq_records(settings.faq_path))

    if not status["embeddingConfigured"]:
        status["warning"] = (
            "Set EMBEDDING_API_BASE and EMBEDDING_API_KEY in backend/.env "
            "(Ollama: same host as MODEL_API_BASE, key local-key)"
        )
        return status

    need_build = not index_ready(settings.index_dir) or (
        settings.build_on_startup and _faq_newer_than_index(settings)
    )
    if need_build:
        try:
            status["recordCount"] = build_faq_index(settings)
            status["built"] = True
            status["indexReady"] = True
        except Exception as error:
            status["buildError"] = str(error)[:400]
            logger.exception("RAG index build failed")
            return status

    status["indexReady"] = index_ready(settings.index_dir)
    if status["indexReady"]:
        from .service import get_rag_service

        svc = get_rag_service()
        svc.preload()
        status["preloaded"] = True

    return status
