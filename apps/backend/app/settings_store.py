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
    default_voice_avatar_map,
    env_file_paths,
    install_root,
    is_frozen,
)

SETTING_FIELDS: list[dict[str, Any]] = []

EDITABLE_KEYS: set[str] = set()


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
    for key, val in os.environ.items():
        if val is not None:
            merged[key] = val
    return merged


def paths_snapshot() -> dict[str, str]:
    return {
        "appDataDir": str(app_data_dir()),
        "envFile": str(primary_env_file()),
        "installDir": str(install_root()),
        "audioDir": os.getenv("AUDIO_OUTPUT_DIR") or str(default_audio_dir()),
        "faqPath": os.getenv("FAQ_PATH") or os.getenv("RAG_FAQ_PATH") or str(default_faq_path()),
        "voiceAvatarMap": os.getenv("VOICE_AVATAR_MAP_PATH") or str(default_voice_avatar_map()),
        "bundledMode": is_frozen(),
    }


def get_snapshot() -> dict[str, Any]:
    return {
        "fields": [],
        "paths": paths_snapshot(),
        "notes": {
            "desktop": (
                "Technical settings are bundled with the app. "
                "Configure MODEL_* and TTS_* in apps/backend/.env (dev) or "
                "%APPDATA%\\PersonaAI\\.env (installed), then rebuild the sidecar."
            ),
        },
    }


def persist_updates(updates: dict[str, Any]) -> list[str]:
    """Desktop builds do not expose editable settings in the UI."""
    _ = updates
    return []
