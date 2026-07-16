"""Rhubarb Lip Sync — mouth cues from audio (not text heuristics)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from app.paths import bundle_dir, is_frozen, repo_root, resolve_path

logger = logging.getLogger(__name__)

# Rhubarb A–H / X → app viseme ids (frontend maps these to VRM expressions)
RHUBARB_TO_VISEME: dict[str, tuple[str, float]] = {
    "A": ("A", 0.95),  # M B P — closed
    "B": ("B", 0.85),  # consonants / slight open
    "C": ("C", 0.9),  # AEI etc — open
    "D": ("D", 1.0),  # wide open
    "E": ("E", 0.9),  # round
    "F": ("F", 0.85),  # F / V
    "G": ("G", 0.85),  # F / V variant
    "H": ("H", 0.9),  # wide
    "X": ("X", 0.7),  # idle / rest
}

Recognizer = Literal["pocketSphinx", "phonetic"]

RHUBARB_PATH: str = ""
RHUBARB_TIMEOUT_SECONDS: float = 60.0


def reload_rhubarb_config() -> None:
    global RHUBARB_PATH, RHUBARB_TIMEOUT_SECONDS
    RHUBARB_PATH = (os.getenv("RHUBARB_PATH") or "").strip()
    RHUBARB_TIMEOUT_SECONDS = float(os.getenv("RHUBARB_TIMEOUT_SECONDS", "60"))


reload_rhubarb_config()


def _candidate_binaries() -> list[Path]:
    names = ("rhubarb.exe", "rhubarb")
    candidates: list[Path] = []

    if RHUBARB_PATH:
        raw = resolve_path(RHUBARB_PATH)
        if raw.is_file():
            candidates.append(raw)
        elif raw.is_dir():
            for name in names:
                candidates.append(raw / name)

    which = shutil.which("rhubarb") or shutil.which("rhubarb.exe")
    if which:
        candidates.append(Path(which))

    search_roots = [
        repo_root() / "tools" / "rhubarb",
        bundle_dir() / "tools" / "rhubarb",
        bundle_dir() / "rhubarb",
    ]
    if is_frozen():
        from app.paths import sidecar_dir

        search_roots.extend(
            [
                sidecar_dir() / "tools" / "rhubarb",
                sidecar_dir().parent / "tools" / "rhubarb",
            ]
        )

    for root in search_roots:
        for name in names:
            candidates.append(root / name)

    return candidates


def find_rhubarb_binary() -> Path | None:
    seen: set[Path] = set()
    for path in _candidate_binaries():
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def rhubarb_ready() -> bool:
    return find_rhubarb_binary() is not None


def rhubarb_status() -> dict[str, Any]:
    binary = find_rhubarb_binary()
    return {
        "provider": "rhubarb",
        "ready": binary is not None,
        "binary": str(binary) if binary else None,
        "timeoutSeconds": RHUBARB_TIMEOUT_SECONDS,
    }


def _closed_timeline(duration_ms: int) -> list[dict[str, Any]]:
    return [
        {
            "startMs": 0,
            "endMs": max(0, duration_ms),
            "viseme": "X",
            "weight": 0.7,
        }
    ]


def _cues_to_visemes(mouth_cues: list[dict[str, Any]], duration_ms: int) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for cue in mouth_cues:
        raw = str(cue.get("value") or "X").strip().upper()
        shape, weight = RHUBARB_TO_VISEME.get(raw, ("X", 0.7))
        start_ms = int(round(float(cue.get("start") or 0) * 1000))
        end_ms = int(round(float(cue.get("end") or 0) * 1000))
        if end_ms <= start_ms:
            end_ms = start_ms + 30
        timeline.append(
            {
                "startMs": max(0, start_ms),
                "endMs": max(0, end_ms),
                "viseme": shape,
                "weight": weight,
            }
        )

    if not timeline:
        return _closed_timeline(duration_ms)

    if duration_ms > 0 and timeline[-1]["endMs"] < duration_ms:
        timeline[-1]["endMs"] = duration_ms
    return timeline


def _pick_recognizer(locale: str) -> Recognizer:
    # pocketSphinx is English-only; phonetic is language-independent (Persian, etc.).
    if (locale or "").lower().startswith("en"):
        return "pocketSphinx"
    return "phonetic"


async def analyze_wav(
    wav_path: str | Path,
    *,
    duration_ms: int,
    dialog_text: str | None = None,
    locale: str = "fa",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Run Rhubarb on a WAV file.

    Returns (viseme dicts, meta). Never raises for missing binary — returns idle mouth.
    """
    path = Path(wav_path)
    meta: dict[str, Any] = {
        "engine": "rhubarb",
        "ok": False,
        "recognizer": None,
        "cueCount": 0,
        "latencyMs": 0,
        "error": None,
    }

    if not path.is_file():
        meta["error"] = f"wav missing: {path}"
        return _closed_timeline(duration_ms), meta

    binary = find_rhubarb_binary()
    if binary is None:
        meta["error"] = "rhubarb binary not found (run scripts/ensure-rhubarb.ps1)"
        logger.warning(meta["error"])
        return _closed_timeline(duration_ms), meta

    recognizer = _pick_recognizer(locale)
    meta["recognizer"] = recognizer

    with tempfile.TemporaryDirectory(prefix="persona-rhubarb-") as tmp:
        tmp_dir = Path(tmp)
        out_json = tmp_dir / "mouth.json"
        dialog_file: Path | None = None
        cmd = [str(binary), "-f", "json", "-r", recognizer, "-o", str(out_json)]

        # Dialog file helps English pocketSphinx; optional for phonetic too.
        if dialog_text and dialog_text.strip():
            dialog_file = tmp_dir / "dialog.txt"
            dialog_file.write_text(dialog_text.strip() + "\n", encoding="utf-8")
            cmd.extend(["--dialogFile", str(dialog_file)])

        cmd.append(str(path.resolve()))

        started = asyncio.get_running_loop().time()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(binary.parent),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=RHUBARB_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                meta["error"] = f"rhubarb timed out after {RHUBARB_TIMEOUT_SECONDS}s"
                logger.warning(meta["error"])
                return _closed_timeline(duration_ms), meta

            meta["latencyMs"] = int((asyncio.get_running_loop().time() - started) * 1000)

            if proc.returncode != 0:
                err = (stderr or b"").decode("utf-8", errors="replace").strip()
                meta["error"] = err or f"rhubarb exit {proc.returncode}"
                logger.warning("Rhubarb failed: %s", meta["error"])
                return _closed_timeline(duration_ms), meta

            if not out_json.is_file():
                # Some builds print JSON to stdout when -o fails
                raw = (stdout or b"").decode("utf-8", errors="replace").strip()
                if not raw:
                    meta["error"] = "rhubarb produced no output"
                    return _closed_timeline(duration_ms), meta
                payload = json.loads(raw)
            else:
                payload = json.loads(out_json.read_text(encoding="utf-8"))

            cues = payload.get("mouthCues") or []
            if not isinstance(cues, list):
                meta["error"] = "invalid mouthCues"
                return _closed_timeline(duration_ms), meta

            # Prefer Rhubarb's own duration when the WAV header lied to us.
            meta_duration = payload.get("metadata") or {}
            rhubarb_ms = int(round(float(meta_duration.get("duration") or 0) * 1000))
            effective_ms = duration_ms
            if rhubarb_ms > 200:
                effective_ms = rhubarb_ms
            elif cues:
                last_end = int(round(float(cues[-1].get("end") or 0) * 1000))
                if last_end > 200:
                    effective_ms = last_end

            timeline = _cues_to_visemes(cues, effective_ms)
            # Drop zero-length idle-only timelines (broken WAV → duration 0)
            if (
                len(timeline) == 1
                and timeline[0]["viseme"] == "X"
                and timeline[0]["endMs"] - timeline[0]["startMs"] < 50
            ):
                meta["error"] = "rhubarb returned empty/zero-duration cues (check WAV headers)"
                meta["ok"] = False
                return _closed_timeline(max(duration_ms, 800)), meta

            meta["ok"] = True
            meta["cueCount"] = len(timeline)
            meta["durationMs"] = effective_ms
            return timeline, meta

        except Exception as exc:  # noqa: BLE001 — surface as soft failure
            meta["latencyMs"] = int((asyncio.get_running_loop().time() - started) * 1000)
            meta["error"] = str(exc)
            logger.exception("Rhubarb analyze failed")
            return _closed_timeline(duration_ms), meta
