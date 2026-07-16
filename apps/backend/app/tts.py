"""OpenAI-compatible HTTP text-to-speech."""

from __future__ import annotations

import logging
import os
import struct
import wave
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx

from app.paths import default_audio_dir, resolve_path

logger = logging.getLogger(__name__)

SpeakingSpeed = Literal["low", "medium", "high"]

DEFAULT_VOICES: list[dict[str, Any]] = [
    {"id": "shimmer", "label": "Shimmer", "voiceAge": "young", "gender": "female"},
    {"id": "nova", "label": "Nova", "voiceAge": "young", "gender": "female"},
    {"id": "coral", "label": "Coral", "voiceAge": "young", "gender": "female"},
    {"id": "sage", "label": "Sage", "voiceAge": "old", "gender": "female"},
    {"id": "alloy", "label": "Alloy", "voiceAge": "young", "gender": "female"},
    {"id": "fable", "label": "Fable", "voiceAge": "child", "gender": "female"},
    {"id": "echo", "label": "Echo", "voiceAge": "young", "gender": "male"},
    {"id": "onyx", "label": "Onyx", "voiceAge": "old", "gender": "male"},
]

_voice_catalog_cache: list[dict[str, Any]] | None = None
AUDIO_OUTPUT_DIR: str = ""


def _env_trim(raw: str | None, default: str = "") -> str:
    if raw is None:
        return default
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text or default


def reload_tts_config() -> None:
    global TTS_API_BASE, TTS_API_KEY, TTS_MODEL, TTS_TIMEOUT_SECONDS
    global TTS_VOICE_FA, TTS_VOICE_EN, AUDIO_OUTPUT_DIR, _voice_catalog_cache

    model_base = _env_trim(os.getenv("MODEL_API_BASE"), "http://127.0.0.1:11434/v1")
    TTS_API_BASE = _env_trim(os.getenv("TTS_API_BASE"), model_base).rstrip("/")
    TTS_API_KEY = _env_trim(os.getenv("TTS_API_KEY"), _env_trim(os.getenv("MODEL_API_KEY"), "local-key"))
    TTS_MODEL = _env_trim(os.getenv("TTS_MODEL"), "tts-1")
    TTS_TIMEOUT_SECONDS = float(os.getenv("TTS_TIMEOUT_SECONDS", os.getenv("MODEL_TIMEOUT_SECONDS", "30")))
    TTS_VOICE_FA = _env_trim(os.getenv("TTS_VOICE_FA"), "shimmer")
    TTS_VOICE_EN = _env_trim(os.getenv("TTS_VOICE_EN"), "alloy")
    raw_audio = _env_trim(os.getenv("AUDIO_OUTPUT_DIR"), "")
    # Always absolute — relative ../../audio broke under the desktop sidecar cwd.
    AUDIO_OUTPUT_DIR = str(resolve_path(raw_audio) if raw_audio else default_audio_dir())
    Path(AUDIO_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    _voice_catalog_cache = None


reload_tts_config()


def _speaking_speed_to_rate(speed: SpeakingSpeed) -> float:
    if speed == "low":
        return 0.9
    if speed == "high":
        return 1.12
    return 1.0


def voice_catalog() -> list[dict[str, Any]]:
    global _voice_catalog_cache
    if _voice_catalog_cache is None:
        _voice_catalog_cache = [dict(row) for row in DEFAULT_VOICES]
    return _voice_catalog_cache


def tts_stack_ready() -> bool:
    if not TTS_API_BASE or not TTS_API_KEY or not TTS_MODEL:
        return False
    if TTS_API_KEY in ("", "local-key", "api-key"):
        return False
    return len(voice_catalog()) > 0


def tts_status() -> dict[str, Any]:
    catalog = voice_catalog()
    return {
        "provider": "openai-compatible",
        "apiBase": TTS_API_BASE,
        "model": TTS_MODEL,
        "voiceCount": len(catalog),
        "defaultVoiceFa": TTS_VOICE_FA,
        "defaultVoiceEn": TTS_VOICE_EN,
    }


def resolve_voice_entry(locale: Literal["fa", "en"], voice_id: str | None) -> dict[str, Any]:
    catalog = voice_catalog()
    by_id = {row["id"]: row for row in catalog}
    if voice_id and voice_id.strip():
        stripped = voice_id.strip()
        if stripped not in by_id:
            raise ValueError(f"Unknown voiceId: {stripped}")
        return by_id[stripped]
    preferred = TTS_VOICE_EN if locale == "en" else TTS_VOICE_FA
    if preferred in by_id:
        return by_id[preferred]
    if catalog:
        return catalog[0]
    raise ValueError(f"No TTS voice available for locale '{locale}'.")


def repair_wav_headers(path: str | Path) -> bool:
    """
    Fix WAV files that use 0xFFFFFFFF chunk sizes (common with some cloud TTS gateways).
    Returns True if the file was modified.
    """
    file_path = Path(path)
    data = bytearray(file_path.read_bytes())
    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return False

    file_size = len(data)
    riff_size = struct.unpack_from("<I", data, 4)[0]
    expected_riff = file_size - 8
    changed = False

    if riff_size != expected_riff:
        struct.pack_into("<I", data, 4, expected_riff)
        changed = True

    offset = 12
    while offset + 8 <= file_size:
        chunk_id = bytes(data[offset : offset + 4])
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        payload = offset + 8

        if chunk_id == b"data":
            real_size = file_size - payload
            if chunk_size != real_size:
                struct.pack_into("<I", data, offset + 4, real_size)
                changed = True
            break

        if chunk_size == 0xFFFFFFFF or payload + chunk_size > file_size:
            # Corrupt / unbounded chunk — stop scanning
            break
        offset = payload + chunk_size + (chunk_size & 1)

    if changed:
        file_path.write_bytes(data)
        logger.info("Repaired WAV headers for %s (size=%s)", file_path.name, file_size)
    return changed


def _duration_from_fmt_and_filesize(path: str | Path) -> int:
    data = Path(path).read_bytes()
    if len(data) < 44 or data[0:4] != b"RIFF":
        return 0
    offset = 12
    byte_rate = 0
    data_bytes = 0
    while offset + 8 <= len(data):
        chunk_id = data[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        payload = offset + 8
        if chunk_id == b"fmt " and chunk_size >= 16:
            _audio_format, _ch, _rate, byte_rate, _align, _bits = struct.unpack_from(
                "<HHIIHH", data, payload
            )
        elif chunk_id == b"data":
            if chunk_size == 0xFFFFFFFF or payload + chunk_size > len(data):
                data_bytes = len(data) - payload
            else:
                data_bytes = chunk_size
            break
        if chunk_size == 0xFFFFFFFF:
            break
        offset = payload + chunk_size + (chunk_size & 1)
    if byte_rate <= 0 or data_bytes <= 0:
        return 0
    return int((data_bytes / float(byte_rate)) * 1000)


def _audio_duration_ms(path: str) -> int:
    repair_wav_headers(path)
    duration = 0
    try:
        with wave.open(path, "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            if rate > 0 and 0 < frames < 100_000_000:
                duration = int((frames / float(rate)) * 1000)
    except (OSError, wave.Error):
        duration = 0

    if duration <= 0 or duration > 120_000:
        duration = _duration_from_fmt_and_filesize(path)

    if duration <= 0:
        # Last resort: assume 24 kHz mono 16-bit PCM after 44-byte header
        size = Path(path).stat().st_size
        pcm = max(0, size - 44)
        duration = int((pcm / 48000.0) * 1000)

    return max(400, min(duration, 120_000))


async def synthesize_speech(
    text: str,
    voice_id: str,
    speaking_speed: SpeakingSpeed = "medium",
) -> tuple[str, str, int]:
    if not tts_stack_ready():
        raise RuntimeError(
            "TTS is not configured. Set TTS_API_BASE, TTS_API_KEY, and TTS_MODEL in .env "
            "(defaults to MODEL_* when TTS_* is omitted)."
        )

    output_name = f"tts_{uuid4().hex}.wav"
    output_file = str(Path(AUDIO_OUTPUT_DIR) / output_name)
    url = f"{TTS_API_BASE.rstrip('/')}/audio/speech"
    headers = {
        "Authorization": f"Bearer {TTS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TTS_MODEL,
        "input": text,
        "voice": voice_id,
        "response_format": "wav",
        "speed": _speaking_speed_to_rate(speaking_speed),
    }

    timeout = httpx.Timeout(TTS_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False, follow_redirects=True) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            detail = response.text[:1500]
            try:
                body = response.json()
                if isinstance(body, dict):
                    err = body.get("error")
                    if isinstance(err, dict) and err.get("message"):
                        detail = str(err["message"])
                    elif body.get("message"):
                        detail = str(body["message"])
                    elif body.get("detail"):
                        detail = str(body["detail"])
            except ValueError:
                pass
            raise RuntimeError(f"TTS API error — HTTP {response.status_code}: {detail}")
        data = response.content
        if not data:
            raise RuntimeError("TTS API returned empty audio.")

    with open(output_file, "wb") as handle:
        handle.write(data)

    repair_wav_headers(output_file)
    duration_ms = _audio_duration_ms(output_file)
    return (f"/audio/{output_name}", output_file, duration_ms)
