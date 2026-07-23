"""Keep console tools (ffmpeg, rhubarb) from flashing a terminal on Windows."""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def hidden_process_kwargs() -> dict[str, Any]:
    if sys.platform != "win32":
        return {}
    # CREATE_NO_WINDOW: console-subsystem binaries stay invisible when spawned
    # from a GUI / PyInstaller sidecar (Tauri desktop).
    return {"creationflags": subprocess.CREATE_NO_WINDOW}
