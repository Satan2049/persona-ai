"""OpenAI-compatible HTTP speech-to-text."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

import httpx

Locale = Literal["fa", "en"]

TRANSCRIPTION_PATH = "/audio/transcriptions"


def _env_trim(raw: str | None, default: str = "") -> str:
    if raw is None:
        return default
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text or default


def reload_stt_config() -> None:
    global STT_API_BASE, STT_API_KEY, STT_MODEL, STT_TIMEOUT_SECONDS

    model_base = _env_trim(os.getenv("MODEL_API_BASE"), "http://127.0.0.1:11434/v1")
    tts_base = _env_trim(os.getenv("TTS_API_BASE"), model_base).rstrip("/")
    STT_API_BASE = _env_trim(os.getenv("STT_API_BASE"), tts_base).rstrip("/")
    STT_API_KEY = _env_trim(
        os.getenv("STT_API_KEY"),
        _env_trim(os.getenv("TTS_API_KEY"), _env_trim(os.getenv("MODEL_API_KEY"), "local-key")),
    )
    STT_MODEL = _env_trim(os.getenv("STT_MODEL"), "whisper-1")
    STT_TIMEOUT_SECONDS = float(
        os.getenv("STT_TIMEOUT_SECONDS", os.getenv("TTS_TIMEOUT_SECONDS", "45"))
    )


reload_stt_config()


def transcription_url() -> str:
    """Full OpenAI-compatible STT endpoint ({base}/audio/transcriptions)."""
    base = STT_API_BASE.rstrip("/")
    if base.endswith(TRANSCRIPTION_PATH):
        return base
    return f"{base}{TRANSCRIPTION_PATH}"


def _locale_to_language(locale: Locale) -> str:
    return "fa" if locale == "fa" else "en"


def stt_stack_ready() -> bool:
    if not STT_API_BASE or not STT_API_KEY or not STT_MODEL:
        return False
    return STT_API_KEY not in ("", "local-key", "api-key")


def stt_status() -> dict[str, Any]:
    return {
        "provider": "openai-compatible",
        "apiBase": STT_API_BASE,
        "model": STT_MODEL,
        "transcribeUrl": transcription_url(),
    }


def _parse_transcription_response(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    try:
        body = json.loads(text)
    except ValueError:
        return text
    if isinstance(body, dict):
        if isinstance(body.get("text"), str):
            return body["text"].strip()
        if isinstance(body.get("transcript"), str):
            return body["transcript"].strip()
    return text


def _convert_to_wav_with_ffmpeg(audio_bytes: bytes, suffix: str) -> bytes | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    with tempfile.TemporaryDirectory(prefix="persona-stt-") as tmp:
        src = Path(tmp) / f"input.{suffix}"
        dst = Path(tmp) / "output.wav"
        src.write_bytes(audio_bytes)
        try:
            subprocess.run(
                [ffmpeg, "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
                capture_output=True,
                check=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return None
        if not dst.is_file():
            return None
        return dst.read_bytes()


def _prepare_audio_upload(
    audio_bytes: bytes,
    filename: str,
    content_type: str | None,
) -> tuple[bytes, str, str]:
    if audio_bytes[:4] == b"RIFF":
        return audio_bytes, "speech.wav", "audio/wav"

    lowered = (filename or "").lower()
    suffix = "webm"
    if lowered.endswith(".ogg"):
        suffix = "ogg"
    elif lowered.endswith(".mp4") or lowered.endswith(".m4a"):
        suffix = "mp4"
    elif lowered.endswith(".wav"):
        suffix = "wav"
    elif content_type and "ogg" in content_type:
        suffix = "ogg"
    elif content_type and "mp4" in content_type:
        suffix = "mp4"

    converted = _convert_to_wav_with_ffmpeg(audio_bytes, suffix)
    if converted:
        return converted, "speech.wav", "audio/wav"

    raise RuntimeError(
        "Unsupported microphone audio format. GapGPT Whisper needs WAV — "
        "update the app or install ffmpeg on PATH to convert WebM/OGG."
    )


async def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str = "speech.wav",
    content_type: str | None = "audio/wav",
    locale: Locale = "fa",
) -> str:
    if not stt_stack_ready():
        raise RuntimeError(
            "STT is not configured. Set STT_API_BASE, STT_API_KEY, and STT_MODEL in .env "
            "(defaults to TTS_*/MODEL_* when STT_* is omitted)."
        )
    if not audio_bytes:
        raise RuntimeError("Empty audio recording.")

    prepared, upload_name, upload_type = _prepare_audio_upload(
        audio_bytes, filename, content_type
    )
    url = transcription_url()
    headers = {"Authorization": f"Bearer {STT_API_KEY}"}
    data = {
        "model": STT_MODEL,
        "language": _locale_to_language(locale),
    }
    files = {
        "file": (upload_name, prepared, upload_type),
    }

    timeout = httpx.Timeout(STT_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False, follow_redirects=True) as client:
        response = await client.post(url, headers=headers, data=data, files=files)
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
            raise RuntimeError(
                f"STT API error — HTTP {response.status_code} @ {url}: {detail}"
            )

        text = _parse_transcription_response(response.text)
        if not text:
            raise RuntimeError("STT API returned empty transcript.")
        return text
