"""Production entrypoint for the FastAPI sidecar (desktop bundle / PyInstaller)."""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


def _append_startup_log(message: str) -> None:
    try:
        appdata = os.environ.get("APPDATA", "").strip()
        if not appdata:
            return
        log_dir = os.path.join(appdata, "PersonaAI", "logs")
        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        with open(os.path.join(log_dir, "sidecar.log"), "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
    except Exception:
        pass


def _ensure_stdio() -> None:
    """Windowed PyInstaller builds leave stdout/stderr as None; uvicorn logging needs them."""
    sink = getattr(_ensure_stdio, "_sink", None)
    if sink is None:
        sink = open(os.devnull, "w", encoding="utf-8")
        _ensure_stdio._sink = sink  # type: ignore[attr-defined]

    if sys.stdout is None:
        sys.stdout = sink
    if sys.stderr is None:
        sys.stderr = sink


def _uvicorn_log_config(level: str) -> dict[str, Any]:
    """Plain formatters only — never use uvicorn DefaultFormatter (TTY / isatty checks)."""
    level_name = level.upper()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(levelname)s:     %(message)s",
            },
            "access": {
                "format": '%(levelname)s:     %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": level_name, "propagate": False},
            "uvicorn.error": {"level": level_name},
            "uvicorn.access": {
                "handlers": ["access"],
                "level": level_name,
                "propagate": False,
            },
        },
    }


def _write_crash_log() -> None:
    try:
        from app.paths import app_data_dir

        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "sidecar.log").write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    _ensure_stdio()
    _append_startup_log("run_prod: main() entered")

    from app.env_bootstrap import ensure_desktop_env_file
    from app.paths import ensure_app_data_dirs

    ensure_app_data_dirs()
    ensure_desktop_env_file()
    _append_startup_log("run_prod: env ready")

    host = os.getenv("PERSONA_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("PERSONA_PORT", "8000"))
    log_level = os.getenv("PERSONA_LOG_LEVEL", "info")
    _append_startup_log(f"run_prod: uvicorn {host}:{port}")

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        log_config=_uvicorn_log_config(log_level),
        use_colors=False,
        access_log=False,
    )


if __name__ == "__main__":
    _ensure_stdio()
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        _write_crash_log()
        raise
