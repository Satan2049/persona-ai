import os
from dataclasses import dataclass

from dotenv import load_dotenv

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"), override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _resolve_path(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    text = os.path.expandvars(os.path.expanduser(text))
    if os.path.isabs(text):
        return text
    return os.path.abspath(os.path.join(_BACKEND_DIR, text))


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
    return RagSettings(
        enabled=_env_bool("RAG_ENABLED", True),
        build_on_startup=_env_bool("RAG_BUILD_ON_STARTUP", True),
        faq_path=_resolve_path(os.getenv("RAG_FAQ_PATH", "../data/faq_dataset.json")),
        index_dir=_resolve_path(os.getenv("RAG_INDEX_DIR", "../data/rag_index")),
        embedding_api_base=embed_base,
        embedding_api_key=embed_key,
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text").strip(),
        embedding_timeout_seconds=float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "30")),
        top_k=max(1, int(os.getenv("RAG_TOP_K", "4"))),
        min_score=float(os.getenv("RAG_MIN_SCORE", "0.35")),
    )
