import os
from dataclasses import dataclass

from dotenv import load_dotenv

from app.paths import (
    backend_dir,
    default_faq_path,
    default_rag_index_dir,
    env_file_paths,
    resolve_path,
)

_BACKEND_DIR = backend_dir()
for _env_path in reversed(env_file_paths()):
    if _env_path.is_file():
        load_dotenv(_env_path, override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _resolve_path(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    return str(resolve_path(text, base=_BACKEND_DIR))


@dataclass(frozen=True)
class RagSettings:
    enabled: bool
    build_on_startup: bool
    faq_path: str
    index_dir: str
    embedding_api_base: str
    embedding_api_key: str
    embedding_model: str
    embedding_timeout_seconds: float
    top_k: int
    min_score: float


def load_rag_settings() -> RagSettings:
    embed_base = os.getenv("EMBEDDING_API_BASE", "").strip().rstrip("/")
    if not embed_base:
        embed_base = os.getenv("MODEL_API_BASE", "http://127.0.0.1:11434/v1").strip().rstrip("/")
    embed_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    if not embed_key:
        embed_key = os.getenv("MODEL_API_KEY", "local-key").strip()
    faq_path = _resolve_path(os.getenv("RAG_FAQ_PATH", "")) or str(default_faq_path())
    index_dir = _resolve_path(os.getenv("RAG_INDEX_DIR", "")) or str(default_rag_index_dir())
    return RagSettings(
        enabled=_env_bool("RAG_ENABLED", True),
        build_on_startup=_env_bool("RAG_BUILD_ON_STARTUP", True),
        faq_path=faq_path,
        index_dir=index_dir,
        embedding_api_base=embed_base,
        embedding_api_key=embed_key,
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text").strip(),
        embedding_timeout_seconds=float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "30")),
        top_k=max(1, int(os.getenv("RAG_TOP_K", "4"))),
        min_score=float(os.getenv("RAG_MIN_SCORE", "0.35")),
    )
