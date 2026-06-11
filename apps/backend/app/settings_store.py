"""Read/write user settings in AppData .env and expose snapshots for the UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, load_dotenv

from app.paths import (
    app_data_dir,
    default_audio_dir,
    default_faq_path,
    default_piper_models_dir,
    default_rag_index_dir,
    default_voice_avatar_map,
    env_file_paths,
    is_frozen,
)

SECRET_KEYS = frozenset({"MODEL_API_KEY", "EMBEDDING_API_KEY"})

SETTING_FIELDS: list[dict[str, Any]] = [
    {"key": "MODEL_API_BASE", "group": "llm", "label": "Chat API base URL", "type": "url"},
    {"key": "MODEL_API_KEY", "group": "llm", "label": "Chat API key", "type": "secret"},
    {"key": "MODEL_NAME", "group": "llm", "label": "Chat model name", "type": "string"},
    {"key": "MODEL_TIMEOUT_SECONDS", "group": "llm", "label": "Chat timeout (seconds)", "type": "number"},
    {"key": "MODEL_MAX_RETRIES", "group": "llm", "label": "Chat max retries", "type": "number"},
    {"key": "MODEL_TEMPERATURE", "group": "llm", "label": "Temperature", "type": "number"},
    {"key": "MODEL_MAX_TOKENS", "group": "llm", "label": "Max reply tokens (0 = no cap)", "type": "number"},
    {"key": "PIPER_BIN", "group": "piper", "label": "Piper executable path", "type": "path"},
    {"key": "PIPER_MODELS_DIR", "group": "piper", "label": "Piper voices folder", "type": "path"},
    {"key": "PIPER_SPEAKER_ID", "group": "piper", "label": "Piper speaker id (optional)", "type": "string"},
    {"key": "PIPER_ALWAYS_SPEAKER", "group": "piper", "label": "Always pass --speaker (0/1)", "type": "string"},
    {"key": "PIPER_TIMEOUT_SECONDS", "group": "piper", "label": "Piper timeout (seconds)", "type": "number"},
    {"key": "RAG_ENABLED", "group": "rag", "label": "RAG enabled", "type": "bool"},
    {"key": "RAG_BUILD_ON_STARTUP", "group": "rag", "label": "Build RAG index on startup", "type": "bool"},
    {"key": "EMBEDDING_API_BASE", "group": "rag", "label": "Embeddings API base URL", "type": "url"},
    {"key": "EMBEDDING_API_KEY", "group": "rag", "label": "Embeddings API key", "type": "secret"},
    {"key": "EMBEDDING_MODEL", "group": "rag", "label": "Embeddings model name", "type": "string"},
    {"key": "EMBEDDING_TIMEOUT_SECONDS", "group": "rag", "label": "Embeddings timeout (seconds)", "type": "number"},
    {"key": "RAG_TOP_K", "group": "rag", "label": "RAG top K", "type": "number"},
    {"key": "RAG_MIN_SCORE", "group": "rag", "label": "RAG min score", "type": "number"},
    {"key": "SOCIAL_EMERGENCY_NUMBER", "group": "safety", "label": "Social emergency number", "type": "string"},
    {"key": "RESEARCHER_NUMBER", "group": "safety", "label": "Researcher contact number", "type": "string"},
]

EDITABLE_KEYS = {row["key"] for row in SETTING_FIELDS}


def primary_env_file() -> Path:
    return app_data_dir() / ".env"


def _read_file_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    raw = dotenv_values(path)
    return {k: v for k, v in raw.items() if k and v is not None}


def _merge_env_sources() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in reversed(env_file_paths()):
        if path.is_file():
            merged.update(_read_file_values(path))
    for key in EDITABLE_KEYS:
        val = os.getenv(key)
        if val is not None:
            merged[key] = val
    return merged


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}…{value[-2:]}"


def paths_snapshot() -> dict[str, str]:
    return {
        "appDataDir": str(app_data_dir()),
        "envFile": str(primary_env_file()),
        "piperModelsDir": os.getenv("PIPER_MODELS_DIR") or str(default_piper_models_dir()),
        "audioDir": os.getenv("AUDIO_OUTPUT_DIR") or str(default_audio_dir()),
        "ragIndexDir": os.getenv("RAG_INDEX_DIR") or str(default_rag_index_dir()),
        "faqPath": os.getenv("RAG_FAQ_PATH") or str(default_faq_path()),
        "voiceAvatarMap": os.getenv("VOICE_AVATAR_MAP_PATH") or str(default_voice_avatar_map()),
        "bundledMode": is_frozen(),
    }


def get_snapshot() -> dict[str, Any]:
    values = _merge_env_sources()
    fields: list[dict[str, Any]] = []
    for spec in SETTING_FIELDS:
        key = spec["key"]
        raw = values.get(key, os.getenv(key, "")) or ""
        entry = {**spec, "value": raw}
        if spec["type"] == "secret" and raw:
            entry["masked"] = _mask_secret(raw)
        fields.append(entry)
    return {
        "fields": fields,
        "paths": paths_snapshot(),
        "notes": {
            "llmModels": (
                "Chat/embedding models are not shipped with Persona AI. "
                "Install Ollama (or another OpenAI-compatible server) separately and set its model name here."
            ),
            "piperVoices": (
                "Place Piper .onnx + .onnx.json pairs in the Piper voices folder shown below. "
                "They are not included in the installer."
            ),
            "ragIndex": "The RAG vector index is built automatically under the RAG index folder.",
            "restart": "Some RAG path changes may require restarting the app.",
        },
    }


def persist_updates(updates: dict[str, Any]) -> list[str]:
    """Merge updates into AppData .env. Returns list of keys written."""
    env_path = primary_env_file()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    current = _read_file_values(env_path)
    if not current and not env_path.is_file():
        for fallback in env_file_paths():
            if fallback.is_file() and fallback != env_path:
                current.update(_read_file_values(fallback))

    written: list[str] = []
    for key, value in updates.items():
        if key not in EDITABLE_KEYS:
            continue
        if key in SECRET_KEYS and (value is None or str(value).strip() == ""):
            continue
        if value is None:
            continue
        text = str(value).strip()
        current[key] = text
        written.append(key)

    lines = [
        "# Persona AI — user settings (managed from the app Settings panel)",
        f"# Location: {env_path}",
        "",
    ]
    groups = ("llm", "piper", "rag", "safety")
    by_group: dict[str, list[dict[str, Any]]] = {g: [] for g in groups}
    for spec in SETTING_FIELDS:
        by_group[spec["group"]].append(spec)

    for group in groups:
        lines.append(f"# --- {group.upper()} ---")
        for spec in by_group[group]:
            key = spec["key"]
            if key in current:
                lines.append(f"{key}={current[key]}")
        lines.append("")

    for key, val in sorted(current.items()):
        if key in EDITABLE_KEYS:
            continue
        lines.append(f"{key}={val}")

    env_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    load_dotenv(env_path, override=True)
    return written
