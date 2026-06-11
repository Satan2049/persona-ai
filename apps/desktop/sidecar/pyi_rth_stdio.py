"""PyInstaller runtime hook: windowed builds have no stdout/stderr until we assign them."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone


def _append_log(message: str) -> None:
    try:
        appdata = os.environ.get("APPDATA", "").strip()
        if not appdata:
            return
        log_dir = os.path.join(appdata, "PersonaAI", "logs")
        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        path = os.path.join(log_dir, "sidecar.log")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
    except Exception:
        pass


_append_log("pyi_rth_stdio: hook start")

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

_append_log("pyi_rth_stdio: stdio ready")
