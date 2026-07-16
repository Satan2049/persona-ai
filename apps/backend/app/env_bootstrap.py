"""Seed and migrate desktop (PyInstaller) environment before the app loads."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from app.paths import (
    app_data_dir,
    bundled_runtime_env_path,
    bundle_dir,
    find_dev_backend_env_file,
    install_root,
    is_frozen,
    resolve_path,
)

PATH_KEYS = frozenset(
    {
        "TTS_API_BASE",
        "STT_API_BASE",
        "AUDIO_OUTPUT_DIR",
        "FAQ_PATH",
        "RAG_FAQ_PATH",
        "VOICE_AVATAR_MAP_PATH",
    }
)

CONFIG_KEYS = frozenset(
    {
        "MODEL_API_BASE",
        "MODEL_API_KEY",
        "MODEL_NAME",
        "TTS_API_BASE",
        "TTS_API_KEY",
        "TTS_MODEL",
        "STT_API_BASE",
        "STT_API_KEY",
        "STT_MODEL",
    }
)

SYNC_KEYS = CONFIG_KEYS | {
    "MODEL_TIMEOUT_SECONDS",
    "MODEL_MAX_RETRIES",
    "MODEL_TEMPERATURE",
    "MODEL_MAX_TOKENS",
    "SOCIAL_EMERGENCY_NUMBER",
    "RESEARCHER_NUMBER",
    "TTS_VOICE_FA",
    "TTS_VOICE_EN",
    "TTS_TIMEOUT_SECONDS",
    "STT_TIMEOUT_SECONDS",
    "PERSONA_BUILD_ID",
}


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


def _sanitize_imported_env(values: dict[str, str]) -> dict[str, str]:
    out = dict(values)
    out.pop("AUDIO_OUTPUT_DIR", None)
    out.pop("FAQ_PATH", None)
    out.pop("RAG_FAQ_PATH", None)
    out.pop("VOICE_AVATAR_MAP_PATH", None)
    for legacy in (
        "PIPER_BIN",
        "PIPER_MODELS_DIR",
        "PIPER_MODEL_PATH",
        "PIPER_VOICE_ID_FA",
        "PIPER_VOICE_ID_EN",
        "PIPER_SPEAKER_ID",
        "PIPER_ALWAYS_SPEAKER",
        "PIPER_TIMEOUT_SECONDS",
    ):
        out.pop(legacy, None)
    return out


def _prepare_bundled_env_for_desktop(values: dict[str, str]) -> dict[str, str]:
    picked = {k: str(values[k]).strip() for k in SYNC_KEYS if values.get(k, "").strip()}
    return _sanitize_imported_env(picked)


def _stored_build_id() -> str:
    path = app_data_dir() / "build-id.txt"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _sync_from_bundled_runtime_env(target: Path) -> bool:
    runtime = bundled_runtime_env_path()
    if not runtime.is_file():
        return False

    bundled = _read_env_file(runtime)
    build_id = bundled.get("PERSONA_BUILD_ID", "").strip()
    if not build_id:
        return False

    if build_id == _stored_build_id() and target.is_file():
        return False

    prepared = _prepare_bundled_env_for_desktop(bundled)
    if not _env_is_configured(prepared):
        return False

    _write_env_file(target, prepared, source=f"sidecar build {build_id}")
    (app_data_dir() / "build-id.txt").write_text(build_id + "\n", encoding="utf-8")
    return True


def ensure_desktop_env_file() -> Path:
    """Ensure %APPDATA%/PersonaAI/.env matches the bundled sidecar build."""
    target = app_data_dir() / ".env"
    if not is_frozen():
        return target

    if _sync_from_bundled_runtime_env(target):
        return target

    existing = _read_env_file(target)
    dev_env = find_dev_backend_env_file()
    if dev_env and dev_env.is_file() and not _was_user_managed(target):
        imported = _sanitize_imported_env(
            _absolutize_paths(_read_env_file(dev_env), dev_env.parent)
        )
        if _env_is_configured(imported):
            merged = dict(existing)
            for key in SYNC_KEYS:
                if imported.get(key, "").strip():
                    merged[key] = imported[key]
            merged = _sanitize_imported_env(merged)
            if merged != existing or not target.is_file():
                _write_env_file(target, merged, source=str(dev_env))
            return target

    if _env_is_configured(existing):
        sanitized = _sanitize_imported_env(existing)
        if sanitized != existing:
            _write_env_file(target, sanitized, source="legacy env cleanup")
        return target

    bundled = bundle_dir() / "config" / "default.env"
    if bundled.is_file():
        template = _read_env_file(bundled)
        if template:
            seeded = _desktop_seed_values(template)
            _write_env_file(target, seeded, source=str(bundled))
            return target

    _write_env_file(target, _desktop_seed_values(), source="desktop defaults")
    return target


def _desktop_seed_values(extra: dict[str, str] | None = None) -> dict[str, str]:
    values = {
        "MODEL_API_BASE": "http://127.0.0.1:11434/v1",
        "MODEL_API_KEY": "local-key",
        "MODEL_NAME": "iranian-model",
        "TTS_MODEL": "tts-1",
        "TTS_VOICE_FA": "shimmer",
        "TTS_VOICE_EN": "alloy",
        "STT_MODEL": "whisper-1",
        "SOCIAL_EMERGENCY_NUMBER": "123",
        "RESEARCHER_NUMBER": "09373759943",
    }
    if extra:
        for key, val in extra.items():
            if val is not None and str(val).strip():
                values[key] = str(val).strip()
    return _sanitize_imported_env(values)
