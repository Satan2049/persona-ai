"""Seed and migrate desktop (PyInstaller) environment before the app loads."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from app.paths import app_data_dir, bundle_dir, find_dev_backend_env_file, is_frozen, resolve_path

PATH_KEYS = frozenset(
    {
        "PIPER_BIN",
        "PIPER_MODELS_DIR",
        "PIPER_MODEL_PATH",
        "AUDIO_OUTPUT_DIR",
        "RAG_FAQ_PATH",
        "RAG_INDEX_DIR",
        "VOICE_AVATAR_MAP_PATH",
    }
)

CONFIG_KEYS = frozenset(
    {
        "MODEL_API_BASE",
        "MODEL_API_KEY",
        "MODEL_NAME",
        "PIPER_BIN",
        "PIPER_MODELS_DIR",
        "EMBEDDING_API_BASE",
        "EMBEDDING_API_KEY",
    }
)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    raw = dotenv_values(path)
    return {k: v for k, v in raw.items() if k and v is not None}


def _env_is_configured(values: dict[str, str]) -> bool:
    return any(values.get(key, "").strip() for key in CONFIG_KEYS)


def _absolutize_paths(values: dict[str, str], anchor: Path) -> dict[str, str]:
    out = dict(values)
    for key in PATH_KEYS:
        raw = out.get(key, "").strip()
        if not raw:
            continue
        expanded = os.path.expandvars(os.path.expanduser(raw))
        if os.path.isabs(expanded):
            out[key] = str(Path(expanded).resolve())
        else:
            out[key] = str(resolve_path(expanded, base=anchor))
    return out


def _write_env_file(path: Path, values: dict[str, str], *, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Persona AI — desktop settings",
        f"# Seeded from: {source}",
        f"# Location: {path}",
        "",
    ]
    for key in sorted(values):
        lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _was_user_managed(path: Path) -> bool:
    if not path.is_file():
        return False
    head = path.read_text(encoding="utf-8", errors="ignore")[:600]
    return "managed from the app Settings panel" in head


def _is_factory_default(values: dict[str, str]) -> bool:
    return values.get("MODEL_API_KEY", "").strip() in ("", "local-key")


def ensure_desktop_env_file() -> Path:
    """Ensure %APPDATA%/PersonaAI/.env exists with usable config for the sidecar."""
    target = app_data_dir() / ".env"
    if not is_frozen():
        return target

    existing = _read_env_file(target)
    dev_env = find_dev_backend_env_file()
    if dev_env and not _was_user_managed(target):
        imported = _absolutize_paths(_read_env_file(dev_env), dev_env.parent)
        if _env_is_configured(imported) and (
            not _env_is_configured(existing) or _is_factory_default(existing)
        ):
            _write_env_file(target, imported, source=str(dev_env))
            return target

    if _env_is_configured(existing):
        return target

    bundled = bundle_dir() / "config" / "default.env"
    if bundled.is_file():
        template = _read_env_file(bundled)
        if template:
            _write_env_file(target, template, source=str(bundled))
            return target

    defaults = {
        "MODEL_API_BASE": "http://127.0.0.1:11434/v1",
        "MODEL_API_KEY": "local-key",
        "MODEL_NAME": "iranian-model",
        "PIPER_BIN": "",
        "PIPER_MODELS_DIR": str(app_data_dir() / "piper_models"),
        "AUDIO_OUTPUT_DIR": str(app_data_dir() / "audio"),
        "RAG_INDEX_DIR": str(app_data_dir() / "rag_index"),
        "RAG_ENABLED": "true",
        "RAG_BUILD_ON_STARTUP": "true",
    }
    _write_env_file(target, defaults, source="desktop defaults")
    return target
