"""Resolve application paths for development, PyInstaller sidecar, and desktop bundles."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_LOADED_ENV_FILES: list[Path] = []


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def sidecar_dir() -> Path:
    """Directory containing the sidecar executable (writable install root)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return backend_dir()


def bundle_dir() -> Path:
    """Read-only bundled resources (PyInstaller _MEIPASS)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return backend_dir()


def backend_dir() -> Path:
    """Python backend package root (`apps/backend`)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    """Monorepo / install root (`persona-ai/` or sidecar folder)."""
    if is_frozen():
        return install_root()
    return backend_dir().parent.parent


def install_root() -> Path:
    """Desktop install directory (parent of `resources/`) or repo root in dev."""
    override = os.getenv("PERSONA_INSTALL_DIR", "").strip()
    if override:
        return Path(os.path.expandvars(os.path.expanduser(override))).resolve()
    if is_frozen():
        sd = sidecar_dir()
        if sd.name.lower() == "resources":
            return sd.parent
        return sd
    return backend_dir().parent.parent


def app_data_dir() -> Path:
    """Writable per-user data (config, audio cache)."""
    override = os.getenv("PERSONA_DATA_DIR", "").strip()
    if override:
        return Path(os.path.expandvars(os.path.expanduser(override))).resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return (base / "PersonaAI").resolve()


def find_dev_backend_env_file() -> Path | None:
    """Locate apps/backend/.env for desktop sidecar (explicit path or repo walk)."""
    override = os.getenv("PERSONA_BACKEND_ENV", "").strip()
    if override:
        path = Path(os.path.expandvars(os.path.expanduser(override))).resolve()
        if path.is_file():
            return path

    if not is_frozen():
        return None

    rels = (Path("apps") / "backend" / ".env", Path("backend") / ".env")
    seen: set[Path] = set()
    for start in (sidecar_dir(), install_root()):
        current = start.resolve()
        for _ in range(12):
            if current in seen:
                break
            seen.add(current)
            for rel in rels:
                candidate = (current / rel).resolve()
                if candidate.is_file():
                    return candidate
            parent = current.parent
            if parent == current:
                break
            current = parent
    return None


def bundled_runtime_env_path() -> Path:
    """PyInstaller-bundled snapshot of apps/backend/.env from the last sidecar build."""
    return bundle_dir() / "config" / "runtime.env"


def load_application_env() -> list[Path]:
    """Load .env layers; later files override earlier ones."""
    global _LOADED_ENV_FILES
    _LOADED_ENV_FILES = []

    bundled = bundle_dir() / "config" / "default.env"
    if is_frozen() and bundled.is_file():
        load_dotenv(bundled, override=True)
        _LOADED_ENV_FILES.append(bundled)

    appdata = app_data_dir() / ".env"
    if appdata.is_file():
        load_dotenv(appdata, override=True)
        _LOADED_ENV_FILES.append(appdata)

    runtime = bundled_runtime_env_path()
    if is_frozen() and runtime.is_file():
        load_dotenv(runtime, override=True)
        _LOADED_ENV_FILES.append(runtime)

    if not is_frozen():
        local = backend_dir() / ".env"
        if local.is_file():
            load_dotenv(local, override=True)
            _LOADED_ENV_FILES.append(local)

    dev = find_dev_backend_env_file()
    if dev and dev.is_file():
        load_dotenv(dev, override=True)
        if dev not in _LOADED_ENV_FILES:
            _LOADED_ENV_FILES.append(dev)

    return list(_LOADED_ENV_FILES)


def loaded_env_files() -> list[Path]:
    return list(_LOADED_ENV_FILES)


def env_path_anchor() -> Path:
    """Base directory for resolving relative paths in .env."""
    if is_frozen():
        dev_env = find_dev_backend_env_file()
        if dev_env:
            return dev_env.parent
        return app_data_dir()
    return backend_dir()


def env_file_paths() -> list[Path]:
    """Legacy list used by settings snapshot; prefer load_application_env()."""
    paths: list[Path] = []
    bundled = bundle_dir() / "config" / "default.env"
    if is_frozen() and bundled.is_file():
        paths.append(bundled)
    paths.append(app_data_dir() / ".env")
    if not is_frozen():
        paths.append(backend_dir() / ".env")
    dev = find_dev_backend_env_file()
    if dev and dev.is_file():
        paths.append(dev)
    return paths


def default_ui_root() -> Path:
    bundled = bundle_dir() / "ui"
    if bundled.is_dir():
        return bundled
    return repo_root() / "ui"


def default_audio_dir() -> Path:
    env = os.getenv("AUDIO_OUTPUT_DIR", "").strip()
    if env:
        return resolve_path(env)
    return app_data_dir() / "audio"


def default_voice_avatar_map() -> Path:
    env = os.getenv("VOICE_AVATAR_MAP_PATH", "").strip()
    if env:
        return resolve_path(env)
    for candidate in (
        app_data_dir() / "voice_avatar_map.json",
        bundle_dir() / "config" / "voice_avatar_map.json",
        repo_root() / "assets" / "config" / "voice_avatar_map.json",
    ):
        if candidate.is_file():
            return candidate
    return repo_root() / "assets" / "config" / "voice_avatar_map.json"


def default_faq_path() -> Path:
    env = os.getenv("FAQ_PATH", "").strip() or os.getenv("RAG_FAQ_PATH", "").strip()
    if env:
        return resolve_path(env)
    bundled = bundle_dir() / "data" / "faq_dataset.json"
    if bundled.is_file():
        return bundled
    return repo_root() / "data" / "faq_dataset.json"


def resolve_path(raw: str, *, base: Path | None = None) -> Path:
    text = raw.strip()
    if not text:
        return Path()
    text = os.path.expandvars(os.path.expanduser(text))
    path = Path(text)
    if path.is_absolute():
        return path.resolve()
    anchor = base or backend_dir()
    return (anchor / path).resolve()


def ensure_app_data_dirs() -> None:
    for folder in (
        app_data_dir(),
        app_data_dir() / "audio",
        app_data_dir() / "logs",
    ):
        folder.mkdir(parents=True, exist_ok=True)
