# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Persona AI FastAPI sidecar."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

ROOT = Path(SPECPATH).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend"
UI = ROOT / "ui"
DATA = ROOT / "data"
CONFIG = ROOT / "assets" / "config"
ICON = ROOT / "apps" / "desktop" / "src-tauri" / "icons" / "icon.ico"

datas = [
    (str(UI), "ui"),
    (str(DATA / "faq_dataset.json"), "data"),
    (str(CONFIG / "voice_avatar_map.json"), "config"),
    (str(CONFIG / "default.env"), "config"),
]
binaries = []
hiddenimports = [
    "app.main",
    "app.paths",
    "app.env_bootstrap",
    "app.rag",
    "app.rag.bootstrap",
    "app.rag.chunking",
    "app.rag.composer",
    "app.rag.config",
    "app.rag.embeddings",
    "app.rag.loader",
    "app.rag.retriever",
    "app.rag.service",
    "app.rag.store",
    "app.rag.types",
    "pydantic_core._pydantic_core",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "anyio._backends._asyncio",
]

for package in ("pydantic_core", "pydantic", "fastapi", "starlette", "numpy"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += collect_submodules("uvicorn")

a = Analysis(
    [str(BACKEND / "run_prod.py")],
    pathex=[str(BACKEND)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(Path(SPECPATH) / "pyi_rth_stdio.py")],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="persona-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.is_file() else None,
)
