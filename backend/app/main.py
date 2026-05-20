import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
import unicodedata
import wave
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"), override=True)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    rag_init: dict[str, Any] = {"enabled": False}
    try:
        from app.rag.bootstrap import initialize_rag

        rag_init = await asyncio.to_thread(initialize_rag)
        if rag_init.get("buildError"):
            logger.warning("RAG index not ready: %s", rag_init.get("buildError"))
        elif rag_init.get("enabled"):
            logger.info(
                "RAG ready: index=%s records=%s built=%s",
                rag_init.get("indexReady"),
                rag_init.get("recordCount"),
                rag_init.get("built"),
            )
    except Exception as error:
        rag_init = {"enabled": False, "error": str(error)[:400]}
        logger.exception("RAG startup failed")
    _app.state.rag = rag_init
    yield


app = FastAPI(
    title="Smart Avatar Offline Backend",
    version="0.1.0",
    lifespan=_app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_API_BASE = os.getenv("MODEL_API_BASE", "http://127.0.0.1:11434/v1")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "local-key")
MODEL_NAME = os.getenv("MODEL_NAME", "iranian-model")
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "25"))
# Total model attempts = 1 + MODEL_MAX_RETRIES (default: 3 retries after errors = 4 attempts).
MODEL_MAX_RETRIES = int(os.getenv("MODEL_MAX_RETRIES", "3"))
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.5"))
# Hard cap on completion length (OpenAI-compatible `max_tokens`). 0 = omit (no server-side cap).
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "380"))


def _env_trim(raw: str | None, default: str = "") -> str:
    if raw is None:
        return default
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text or default


SOCIAL_EMERGENCY_NUMBER = _env_trim(os.getenv("SOCIAL_EMERGENCY_NUMBER"), "123")
RESEARCHER_NUMBER = _env_trim(os.getenv("RESEARCHER_NUMBER"), "09373759943")

PIPER_BIN_RAW = _env_trim(os.getenv("PIPER_BIN"), "piper")
PIPER_SPEAKER_ID = os.getenv("PIPER_SPEAKER_ID", "")
# If "true"/"1", always pass --speaker (uses PIPER_SPEAKER_ID or 0). Fixes ONNX "Missing Input: sid" when JSON omits num_speakers.
PIPER_ALWAYS_SPEAKER = _env_trim(os.getenv("PIPER_ALWAYS_SPEAKER"), "").lower() in ("1", "true", "yes")
PIPER_TIMEOUT_SECONDS = int(os.getenv("PIPER_TIMEOUT_SECONDS", "30"))


def _resolve_path_from_backend_dir(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    text = os.path.expandvars(os.path.expanduser(text))
    if os.path.isabs(text):
        return text
    return os.path.abspath(os.path.join(_BACKEND_DIR, text))


def _looks_like_filesystem_path(value: str) -> bool:
    if os.path.sep in value:
        return True
    if os.altsep and os.altsep in value:
        return True
    if len(value) > 1 and value[1] == ":":
        return True
    return value.startswith("./") or value.startswith(".\\")


def _resolve_piper_bin(raw: str) -> str:
    text = _env_trim(raw, "piper") or "piper"
    expanded = os.path.expandvars(os.path.expanduser(text))
    if _looks_like_filesystem_path(expanded):
        resolved = (
            os.path.normpath(expanded)
            if os.path.isabs(expanded)
            else _resolve_path_from_backend_dir(expanded)
        )
        return resolved
    found = shutil.which(expanded)
    if found:
        return found
    if os.name == "nt" and not expanded.lower().endswith(".exe"):
        found_exe = shutil.which(f"{expanded}.exe")
        if found_exe:
            return found_exe
    return expanded


def _piper_binary_ready(path: str) -> bool:
    return bool(path and (os.path.isfile(path) or shutil.which(path)))


_default_audio_dir = os.path.abspath(os.path.join(_BACKEND_DIR, "audio"))
AUDIO_OUTPUT_DIR = _resolve_path_from_backend_dir(
    os.getenv("AUDIO_OUTPUT_DIR", _default_audio_dir)
)
PIPER_MODEL_PATH = _resolve_path_from_backend_dir(os.getenv("PIPER_MODEL_PATH", ""))
PIPER_MODELS_DIR = _resolve_path_from_backend_dir(os.getenv("PIPER_MODELS_DIR", "../piper_models"))
PIPER_BIN = _resolve_piper_bin(PIPER_BIN_RAW)
VOICE_AVATAR_MAP_PATH = _resolve_path_from_backend_dir(
    os.getenv("VOICE_AVATAR_MAP_PATH", "../voice_avatar_map.json")
)

_voice_catalog_cache: list[dict[str, Any]] | None = None
_voice_avatar_map_cache: dict[str, Any] | None = None


def _piper_model_onnx_exists() -> bool:
    return bool(PIPER_MODEL_PATH and os.path.isfile(PIPER_MODEL_PATH))


def _piper_model_json_exists() -> bool:
    return bool(PIPER_MODEL_PATH and os.path.isfile(f"{PIPER_MODEL_PATH}.json"))


def _infer_voice_locale(voice_id: str, meta: dict[str, Any]) -> Literal["fa", "en"]:
    lang = meta.get("language") if isinstance(meta.get("language"), dict) else {}
    code = str(lang.get("code", "")).lower()
    family = str(lang.get("family", "")).lower()
    if family == "fa" or code.startswith("fa"):
        return "fa"
    if family == "en" or code.startswith("en"):
        return "en"
    vid = voice_id.lower()
    if vid.startswith("fa_ir") or vid.startswith("fa-") or vid.startswith("fa_"):
        return "fa"
    if vid.startswith("en_") or vid.startswith("en-"):
        return "en"
    if "en" in vid and "fa" not in vid[:4]:
        return "en"
    return "fa"


def _voice_display_label(meta: dict[str, Any], voice_id: str) -> str:
    lang = meta.get("language") if isinstance(meta.get("language"), dict) else {}
    native = str(lang.get("name_native") or lang.get("name_english") or "").strip()
    dataset = str(meta.get("dataset") or "").strip()
    audio = meta.get("audio") if isinstance(meta.get("audio"), dict) else {}
    quality = str(audio.get("quality") or "").strip()
    bits = [b for b in (native, dataset, quality) if b]
    if bits:
        return " · ".join(bits)
    return voice_id.replace("_", " ")


def _load_voice_avatar_map_file() -> dict[str, Any]:
    global _voice_avatar_map_cache
    if _voice_avatar_map_cache is not None:
        return _voice_avatar_map_cache
    data: dict[str, Any] = {}
    if os.path.isfile(VOICE_AVATAR_MAP_PATH):
        try:
            with open(VOICE_AVATAR_MAP_PATH, encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    data = loaded
        except (OSError, ValueError, TypeError):
            data = {}
    _voice_avatar_map_cache = data
    return data


def _voice_map_row(raw_all: dict[str, Any], voice_id: str) -> dict[str, Any]:
    """Return per-voice map row; keys in JSON are matched case-insensitively (Windows paths / ids)."""
    if not isinstance(raw_all, dict):
        return {}
    direct = raw_all.get(voice_id)
    if isinstance(direct, dict):
        return direct
    lowered = voice_id.lower()
    for key, val in raw_all.items():
        if key == "*" or not isinstance(key, str):
            continue
        if isinstance(val, dict) and key.lower() == lowered:
            return val
    return {}


def _voice_age_for_voice_id(voice_id: str) -> Literal["child", "young", "old"]:
    raw_all = _load_voice_avatar_map_file()
    star = raw_all.get("*") if isinstance(raw_all.get("*"), dict) else {}
    row = _voice_map_row(raw_all, voice_id)
    merged: dict[str, Any] = {**star, **row}
    va = str(merged.get("voiceAge", merged.get("voice_age", "young"))).lower()
    if va not in ("child", "young", "old"):
        return "young"
    return va  # type: ignore[return-value]


def _build_voice_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_voice(onnx_path: str) -> None:
        if not onnx_path or not os.path.isfile(onnx_path):
            return
        voice_id = os.path.splitext(os.path.basename(onnx_path))[0]
        if voice_id in seen:
            return
        json_path = f"{onnx_path}.json"
        if not os.path.isfile(json_path):
            return
        meta: dict[str, Any] = {}
        try:
            with open(json_path, encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    meta = loaded
        except (OSError, ValueError, TypeError):
            meta = {}
        locale = _infer_voice_locale(voice_id, meta)
        issues = _validate_voice_meta(meta)
        try:
            num_sp = int(meta.get("num_speakers", 1))
        except (TypeError, ValueError):
            num_sp = 1
        sp_map = meta.get("speaker_id_map")
        named_count = len(sp_map) if isinstance(sp_map, dict) else 0
        voice_age = _voice_age_for_voice_id(voice_id)
        catalog.append(
            {
                "id": voice_id,
                "label": _voice_display_label(meta, voice_id),
                "locale": locale,
                "path": onnx_path,
                "issues": issues,
                "numSpeakers": num_sp,
                "namedSpeakerCount": named_count,
                "voiceAge": voice_age,
            }
        )
        seen.add(voice_id)

    if os.path.isdir(PIPER_MODELS_DIR):
        for entry in sorted(os.listdir(PIPER_MODELS_DIR)):
            if not entry.endswith(".onnx"):
                continue
            add_voice(os.path.join(PIPER_MODELS_DIR, entry))
    if PIPER_MODEL_PATH:
        add_voice(PIPER_MODEL_PATH)

    catalog.sort(key=lambda row: (row["locale"], row["id"].lower()))
    return catalog


def voice_catalog() -> list[dict[str, Any]]:
    global _voice_catalog_cache
    if _voice_catalog_cache is None:
        _voice_catalog_cache = _build_voice_catalog()
    return _voice_catalog_cache


def _tts_stack_ready() -> bool:
    if not _piper_binary_ready(PIPER_BIN):
        return False
    voices = voice_catalog()
    return any(os.path.isfile(v["path"]) and os.path.isfile(f"{v['path']}.json") for v in voices)


_UI_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, "..", "ui"))

SYSTEM_PROMPT_FA = (
    "You are a supportive psychological guidance assistant for Iranian users. "
    "Always reply in Persian (Farsi) using Persian script. "
    "Do not use Arabic script or Arabic dialect; do not switch to English unless the user explicitly asks for English. "
    "Be empathetic and practical. Do not diagnose. "
    "For high-risk self-harm content, advise urgent professional/emergency help in Persian. "
    f"When appropriate (especially in crises or when the user needs human contact), you may share: "
    f"شماره اورژانس اجتماعی {SOCIAL_EMERGENCY_NUMBER}، شماره پژوهشگر {RESEARCHER_NUMBER}. "
    "Keep every reply short: aim for about 3–6 short sentences unless the user explicitly asks for a longer explanation. "
    "No long essays, no numbered lists longer than five items, and no repeating the same idea in different words."
)

SYSTEM_PROMPT_EN = (
    "You are a supportive psychological guidance assistant. "
    "Always reply in clear English only. Do not use Persian or other languages unless the user explicitly asks to switch. "
    "Be empathetic and practical. Do not diagnose. "
    "For high-risk self-harm content, advise urgent professional or emergency help in English. "
    f"When appropriate (especially in crises or when the user needs human contact), you may share: "
    f"Social Emergency number {SOCIAL_EMERGENCY_NUMBER}, Researcher number {RESEARCHER_NUMBER}. "
    "Keep every reply short: aim for about 3–6 short sentences unless the user explicitly asks for more depth. "
    "No long essays, no numbered lists longer than five items, and no repeating the same idea in different words."
)

_COMPACT_RETRY_SUFFIX_FA = (
    "\n\nپاسخ قبلی به خاطر محدودیت طول ناتمام ماند. "
    "این بار فقط ۲ تا ۴ جملهٔ کوتاه و کامل بنویس و با نقطه تمام کن."
)
_COMPACT_RETRY_SUFFIX_EN = (
    "\n\nYour previous reply hit the length limit and was cut off. "
    "This time write only 2–4 short, complete sentences and end on a full stop."
)

_SENTENCE_END_RE = re.compile(r'[.!?؟۔…؛][\'"\)\]»\s]*$')
_SENTENCE_BOUNDARY_RE = re.compile(r'[.!?؟۔…؛][\'"\)\]»\s]*')

HIGH_RISK_TERMS = [
    "suicide",
    "kill myself",
    "self-harm",
    "end my life",
    "hurt myself",
    "خودکشی",
    "به خودم آسیب",
    "میخوام بمیرم",
    "می خواهم بمیرم",
    "زندگی را تمام",
    "آسیب به خودم",
]

ESCALATION_RESPONSE_FA = (
    "من واقعاً متأسفم که این حس را داری. امنیت تو از همه‌چیز مهم‌تر است. "
    "اگر در خطر فوری هستی یا ممکن است به خودت آسیب بزنی، همین الان با اورژانس اجتماعی "
    f"({SOCIAL_EMERGENCY_NUMBER}) یا خط‌های رسمی کمک‌های فوری تماس بگیر "
    "یا از یک نفر مطمئن بخواه کنارت بماند. "
    f"برای ارتباط با پژوهشگر می‌توانی با {RESEARCHER_NUMBER} تماس بگیری. "
    "می‌توانم قدم‌به‌قدم همراهت باشم، اما کمک انسانی فوری هم بسیار مهم است."
)

ESCALATION_RESPONSE_EN = (
    "I am really sorry you are feeling this way. Your safety comes first. "
    f"If you are in immediate danger or might hurt yourself, call Social Emergency ({SOCIAL_EMERGENCY_NUMBER}) "
    "or local emergency services now, "
    "or ask someone you trust to stay with you. "
    f"For researcher contact, call {RESEARCHER_NUMBER}. "
    "I can still walk through next steps with you, but urgent in-person help matters a great deal."
)

DIAGNOSTIC_BLOCK_TERMS = [
    "you have depression",
    "you are bipolar",
    "you have ocd",
    "تشخیص",
    "تو افسردگی داری",
    "تو دوقطبی هستی",
]

_EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U000025E6"
    "\U00002600-\U000026FF"
    "\U000023E9-\U000023FA"
    "\u200D"
    "\uFE0F"
    "]+",
    flags=re.UNICODE,
)


def _strip_for_tts(text: str) -> str:
    """Remove emoji, markdown, and common stage directions so Piper speaks natural language only."""
    t = (text or "").strip()
    if not t:
        return ""
    t = _EMOJI_RE.sub(" ", t)
    t = re.sub(r"\*[^*\n]+\*", " ", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`[^`\n]+`", " ", t)
    t = re.sub(r"^\s*>\s?", "", t, flags=re.MULTILINE)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    out_chars: list[str] = []
    for ch in t:
        cat = unicodedata.category(ch)
        if cat == "So" and ord(ch) >= 0x2000:
            continue
        out_chars.append(ch)
    t = "".join(out_chars)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _tts_fallback_line(locale: Literal["fa", "en"]) -> str:
    return (
        "متن قابل پخش صوتی نبود؛ پاسخ کامل را در بالا ببین."
        if locale == "fa"
        else "There was nothing suitable to speak aloud; please read my full reply above."
    )


def _validate_voice_meta(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(meta.get("language"), dict):
        issues.append("missing language")
    else:
        lang = meta["language"]
        if not str(lang.get("code") or lang.get("family") or "").strip():
            issues.append("language.code/family empty")
    audio = meta.get("audio")
    if not isinstance(audio, dict):
        issues.append("missing audio block")
    else:
        try:
            sr = int(audio.get("sample_rate", 0))
            if sr <= 0:
                issues.append("audio.sample_rate invalid")
        except (TypeError, ValueError):
            issues.append("audio.sample_rate invalid")
    return issues


def _length_scale_for_speaking_speed(speed: Literal["low", "medium", "high"]) -> float:
    # Piper: length_scale > 1 is slower, < 1 is faster (default 1.0).
    if speed == "low":
        return 1.22
    if speed == "high":
        return 0.78
    return 1.0


def _http_status_should_retry(status: int) -> bool:
    if status in (408, 429):
        return True
    return 500 <= status <= 599

os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_OUTPUT_DIR), name="audio")


class ChatRequest(BaseModel):
    sessionId: str = Field(min_length=1)
    userText: str = Field(min_length=1)
    emotionHint: str | None = None
    locale: Literal["fa", "en"] = "fa"
    voiceId: str | None = Field(default=None, description="Piper voice id; must match locale")
    speakingSpeed: Literal["low", "medium", "high"] = "medium"
    avatarFaceAge: Literal["child", "young", "old"] = "young"


class VisemeItem(BaseModel):
    startMs: int
    endMs: int
    viseme: str
    weight: float


class ChatResponse(BaseModel):
    assistantText: str
    audioPath: str
    visemes: list[VisemeItem]
    meta: dict

EVAL_STATS = {
    "requests": 0,
    "highRiskRequests": 0,
    "avgModelMs": 0.0,
    "avgTtsMs": 0.0,
    "avgTotalMs": 0.0,
    "avgAudioDurationMs": 0.0,
}


def _get_audio_duration_ms(audio_file_path: str) -> int:
    with wave.open(audio_file_path, "rb") as wav_file:
        frames = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
    if frame_rate <= 0:
        return 1200
    return max(500, int((frames / frame_rate) * 1000))


def _classify_viseme(char: str) -> tuple[str, float]:
    if char.isascii():
        x = char.lower()
        if x in "mbp":
            return ("viseme_closed", 0.9)
        if x in "fv":
            return ("viseme_fv", 0.8)
        if x in "aeiouy":
            return ("viseme_open", 0.9)
        if x in "shtdjwcngrlkzxq":
            return ("viseme_tight", 0.7)
        return ("viseme_open", 0.65)
    if char in "مبپ":
        return ("viseme_closed", 0.9)
    if char in "فوق":
        return ("viseme_fv", 0.8)
    if char in "اآیوeao":
        return ("viseme_open", 0.9)
    if char in "سشزژتدnlr":
        return ("viseme_tight", 0.7)
    return ("viseme_open", 0.65)


def _build_viseme_timeline(text: str, duration_ms: int) -> list[VisemeItem]:
    chars = [char for char in text if not char.isspace()]
    if not chars:
        return [VisemeItem(startMs=0, endMs=duration_ms, viseme="viseme_closed", weight=0.7)]

    unit = max(55, duration_ms // len(chars))
    cursor = 0
    timeline: list[VisemeItem] = []
    for char in chars:
        viseme, weight = _classify_viseme(char)
        start_ms = cursor
        end_ms = min(duration_ms, start_ms + unit)
        if end_ms <= start_ms:
            end_ms = min(duration_ms, start_ms + 40)
        timeline.append(
            VisemeItem(startMs=start_ms, endMs=end_ms, viseme=viseme, weight=weight)
        )
        cursor = end_ms
        if cursor >= duration_ms:
            break

    if timeline and timeline[-1].endMs < duration_ms:
        timeline.append(
            VisemeItem(
                startMs=timeline[-1].endMs,
                endMs=duration_ms,
                viseme="viseme_closed",
                weight=0.75,
            )
        )
    return timeline


def _extract_assistant_text(model_payload: dict[str, Any]) -> str:
    choices = model_payload.get("choices", [])
    if not choices:
        return ""
    first = choices[0]
    message = first.get("message") or first.get("delta") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def _parse_completion(model_payload: dict[str, Any]) -> tuple[str, str | None]:
    choices = model_payload.get("choices", [])
    if not choices:
        return "", None
    first = choices[0]
    finish = first.get("finish_reason")
    if isinstance(finish, str):
        finish_reason: str | None = finish.strip().lower() or None
    else:
        finish_reason = None
    return _extract_assistant_text(model_payload), finish_reason


def _system_prompt_with_length_cap(
    base: str, locale: Literal["fa", "en"]
) -> str:
    if MODEL_MAX_TOKENS <= 0:
        return base
    if locale == "fa":
        return (
            f"{base}\n\n"
            f"محدودیت سخت: کل پاسخ در حدود {MODEL_MAX_TOKENS} توکن. "
            "۳ تا ۶ جملهٔ کوتاه و کامل بنویس و حتماً با جملهٔ پایانی تمام کن؛ "
            "هرگز وسط جمله یا وسط کلمه قطع نکن—اگر جا کم است، زودتر تمام کن."
        )
    return (
        f"{base}\n\n"
        f"Hard cap: the entire reply must fit in about {MODEL_MAX_TOKENS} tokens. "
        "Use 3–6 short, complete sentences and finish on a closed sentence—"
        "never stop mid-sentence or mid-word; if space is tight, wrap up sooner."
    )


def _ends_sentence(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_SENTENCE_END_RE.search(t))


def _trim_to_complete_sentence(text: str) -> str:
    t = (text or "").strip()
    if not t or _ends_sentence(t):
        return t
    last_end = 0
    for match in _SENTENCE_BOUNDARY_RE.finditer(t):
        last_end = match.end()
    if last_end <= 0:
        return t
    trimmed = t[:last_end].strip()
    min_keep = max(12, int(len(t) * 0.12))
    if len(trimmed) >= min_keep:
        return trimmed
    return t


def _finalize_assistant_text(
    text: str, finish_reason: str | None
) -> tuple[str, dict[str, Any]]:
    info: dict[str, Any] = {
        "finishReason": finish_reason,
        "wasLengthCapped": finish_reason == "length",
        "trimmedForLength": False,
        "retriedCompact": False,
    }
    t = (text or "").strip()
    if not t:
        return t, info

    length_capped = finish_reason == "length"
    if length_capped or not _ends_sentence(t):
        trimmed = _trim_to_complete_sentence(t)
        if trimmed != t:
            info["trimmedForLength"] = True
            t = trimmed

    info["needsCompactRetry"] = length_capped and not _ends_sentence(t)
    return t, info


def _is_high_risk_text(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in HIGH_RISK_TERMS)


def _needs_diagnostic_safety_rewrite(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in DIAGNOSTIC_BLOCK_TERMS)


def _safe_non_diagnostic_rewrite(original_text: str, locale: Literal["fa", "en"]) -> str:
    if locale == "en":
        return (
            "I hear you, and I want to stay with you thoughtfully. "
            "I cannot give a clinical diagnosis, but we can work on how you feel right now, "
            "day-to-day stressors, and practical steps to feel steadier. "
            f"{original_text}"
        )
    return (
        "صدایت را می‌شنوم و می‌خواهم با دقت کنارت باشم. "
        "من نمی‌توانم تشخیص بالینی بدهم، اما می‌توانیم روی احساسات فعالت، عوامل استرس روزانه "
        "و گام‌های عملی برای آرام‌تر شدن با هم کار کنیم. "
        f"{original_text}"
    )


def _piper_windows_exit_hint(returncode: int) -> str:
    if os.name != "nt":
        return ""
    hints: dict[int, str] = {
        # 0xC0000135 STATUS_DLL_NOT_FOUND — Piper exits before printing stderr
        3221225781: (
            " Windows NTSTATUS 0xC0000135 (DLL could not load): unpack the official Piper "
            "Windows amd64 release so piper.exe and every shipped .dll stay in the same folder; "
            "install Microsoft Visual C++ Redistributable 2015–2022 (x64); "
            "do not mix 32-bit and 64-bit binaries."
        ),
        3221225477: (
            " Windows NTSTATUS 0xC0000005 (access violation): incompatible ONNX/onnxruntime "
            "or corrupted Piper install."
        ),
    }
    return hints.get(returncode, "")


def _piper_speaker_cli_args(num_speakers: int, named_speaker_count: int) -> list[str]:
    """Piper multi-speaker ONNX models require --speaker (sid). Single-speaker usually omits it."""
    sid = _env_trim(os.getenv("PIPER_SPEAKER_ID"), "")
    if sid:
        return ["--speaker", sid]
    needs_default = (
        num_speakers > 1
        or named_speaker_count > 0
        or PIPER_ALWAYS_SPEAKER
    )
    if needs_default:
        return ["--speaker", "0"]
    return []


def _synthesize_with_piper(
    text: str,
    model_path: str,
    length_scale: float,
    num_speakers: int = 1,
    named_speaker_count: int = 0,
) -> tuple[str, str]:
    if not model_path:
        raise RuntimeError("No Piper model path selected.")
    if not os.path.isfile(model_path):
        raise RuntimeError(f"Piper model file missing: {model_path}")
    onnx_json = f"{model_path}.json"
    if not os.path.isfile(onnx_json):
        raise RuntimeError(f"Piper model config missing next to ONNX: {onnx_json}")
    if not _piper_binary_ready(PIPER_BIN):
        tip = (
            f" Set PIPER_BIN in backend/.env to piper.exe (raw={PIPER_BIN_RAW!r}, resolved={PIPER_BIN!r})."
            if os.name == "nt"
            else f" Set PIPER_BIN to the Piper executable path or install Piper on PATH "
            f"(raw={PIPER_BIN_RAW!r}, resolved={PIPER_BIN!r})."
        )
        raise RuntimeError("Piper executable not found." + tip)

    output_name = f"tts_{uuid4().hex}.wav"
    output_file = os.path.join(AUDIO_OUTPUT_DIR, output_name)

    cmd = [PIPER_BIN, "--model", model_path, "--output_file", output_file]
    cmd.extend(["--length_scale", str(length_scale)])
    cmd.extend(_piper_speaker_cli_args(num_speakers, named_speaker_count))
    if os.getenv("PIPER_DEBUG", "").strip().lower() in ("1", "true", "yes"):
        cmd.append("--debug")

    run_env = os.environ.copy()
    piper_cwd: str | None = None
    if os.path.isfile(PIPER_BIN):
        piper_home = os.path.dirname(os.path.abspath(PIPER_BIN))
        piper_cwd = piper_home
        run_env["PATH"] = piper_home + os.pathsep + run_env.get("PATH", "")

    try:
        subprocess.run(
            cmd,
            input=text,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            capture_output=True,
            timeout=PIPER_TIMEOUT_SECONDS,
            cwd=piper_cwd,
            env=run_env,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Piper binary not found when launching subprocess. "
            f"Check PIPER_BIN (raw={PIPER_BIN_RAW!r}, resolved={PIPER_BIN!r}). "
            "On Windows use the full path to piper.exe."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Piper synthesis timed out.") from error
    except subprocess.CalledProcessError as error:
        err_raw = error.stderr
        out_raw = error.stdout
        err_out = (
            err_raw.strip()
            if isinstance(err_raw, str)
            else (err_raw or b"").decode("utf-8", errors="ignore").strip()
        )
        std_out = (
            out_raw.strip()
            if isinstance(out_raw, str)
            else (out_raw or b"").decode("utf-8", errors="ignore").strip()
        )
        detail_parts = [f"exit_code={error.returncode}"]
        if err_out:
            detail_parts.append(f"stderr={err_out}")
        if std_out:
            detail_parts.append(f"stdout={std_out}")
        hint = (
            " Empty Piper stderr/stdout: try running piper.exe manually from CMD; "
            "set PIPER_DEBUG=1 in .env for --debug."
            if not err_out and not std_out
            else ""
        )
        win_hint = _piper_windows_exit_hint(error.returncode)
        sid_hint = ""
        if "sid" in err_out.lower() or "missing input" in err_out.lower():
            sid_hint = (
                " This ONNX voice expects a speaker id: set PIPER_SPEAKER_ID (e.g. 0) in .env, "
                "or set PIPER_ALWAYS_SPEAKER=1 to always pass --speaker 0 when the model omits num_speakers."
            )
        raise RuntimeError(
            "Piper synthesis failed: " + "; ".join(detail_parts) + hint + win_hint + sid_hint
        ) from error

    return (f"/audio/{output_name}", output_file)


def _update_running_average(old_avg: float, count: int, new_value: float) -> float:
    if count <= 1:
        return float(new_value)
    return old_avg + ((new_value - old_avg) / count)


async def _post_chat_completion(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Model API error — HTTP {response.status_code}: {response.text[:1500]}")
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(
            "Model response was not valid JSON. "
            f"Raw (truncated): {response.text[:800]}"
        ) from exc


async def _call_llm(
    user_text: str,
    system_prompt: str,
    *,
    locale: Literal["fa", "en"] = "fa",
) -> tuple[str, int, dict[str, Any]]:
    """Returns (assistant_text, attempts_used, model_meta). Retries on transport/API errors."""
    base = MODEL_API_BASE.rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {MODEL_API_KEY}",
        "Content-Type": "application/json",
    }

    def build_payload(system_content: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": MODEL_NAME,
            "temperature": MODEL_TEMPERATURE,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_text},
            ],
        }
        if MODEL_MAX_TOKENS > 0:
            payload["max_tokens"] = MODEL_MAX_TOKENS
        return payload

    last_error: str | None = None
    timeout = httpx.Timeout(MODEL_TIMEOUT_SECONDS)
    max_attempts = max(1, MODEL_MAX_RETRIES + 1)
    llm_meta: dict[str, Any] = {}

    async with httpx.AsyncClient(
        timeout=timeout,
        trust_env=False,
        follow_redirects=True,
    ) as client:
        for attempt in range(max_attempts):
            try:
                body = await _post_chat_completion(
                    client, url, headers, build_payload(system_prompt)
                )
                assistant_text, finish_reason = _parse_completion(body)
                if not assistant_text:
                    last_error = "Model returned empty assistant text."
                    if attempt + 1 < max_attempts:
                        await asyncio.sleep(0.35 * (attempt + 1))
                        continue
                    raise RuntimeError(
                        "Model returned empty assistant text. "
                        f"Payload preview: {str(body)[:900]}"
                    )

                assistant_text, llm_meta = _finalize_assistant_text(
                    assistant_text, finish_reason
                )

                if llm_meta.get("needsCompactRetry") and MODEL_MAX_TOKENS > 0:
                    compact_suffix = (
                        _COMPACT_RETRY_SUFFIX_FA
                        if locale == "fa"
                        else _COMPACT_RETRY_SUFFIX_EN
                    )
                    try:
                        compact_body = await _post_chat_completion(
                            client,
                            url,
                            headers,
                            build_payload(system_prompt + compact_suffix),
                        )
                        compact_text, compact_finish = _parse_completion(compact_body)
                        if compact_text:
                            compact_text, compact_meta = _finalize_assistant_text(
                                compact_text, compact_finish
                            )
                            if _ends_sentence(compact_text) or len(compact_text) < len(
                                assistant_text
                            ):
                                assistant_text = compact_text
                                llm_meta = compact_meta
                                llm_meta["retriedCompact"] = True
                    except (RuntimeError, httpx.HTTPError):
                        pass

                llm_meta.pop("needsCompactRetry", None)
                return (assistant_text, attempt + 1, llm_meta)

            except RuntimeError as error:
                last_error = str(error)
                if "Model API error" in last_error and attempt + 1 < max_attempts:
                    status_match = re.search(r"HTTP (\d+)", last_error)
                    if status_match and _http_status_should_retry(int(status_match.group(1))):
                        await asyncio.sleep(0.35 * (attempt + 1))
                        continue
                if attempt + 1 < max_attempts and "empty assistant" in last_error:
                    await asyncio.sleep(0.35 * (attempt + 1))
                    continue
                raise
            except httpx.HTTPError as error:
                last_error = str(error)
                if attempt + 1 < max_attempts:
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                break

    raise RuntimeError(f"Model call failed after {max_attempts} attempt(s): {last_error}")


def _resolve_voice_entry(locale: Literal["fa", "en"], voice_id: str | None) -> dict[str, Any]:
    catalog = voice_catalog()
    if not catalog:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Piper voices found. Add .onnx and matching .onnx.json under PIPER_MODELS_DIR "
                "or configure PIPER_MODEL_PATH."
            ),
        )
    by_id = {row["id"]: row for row in catalog}
    if voice_id and voice_id.strip():
        stripped = voice_id.strip()
        if stripped not in by_id:
            raise HTTPException(status_code=400, detail=f"Unknown voiceId: {stripped}")
        entry = by_id[stripped]
        if entry["locale"] != locale:
            raise HTTPException(
                status_code=400,
                detail=f"Voice '{stripped}' is registered for locale '{entry['locale']}', not '{locale}'.",
            )
        return entry
    env_key = "PIPER_VOICE_ID_EN" if locale == "en" else "PIPER_VOICE_ID_FA"
    preferred = _env_trim(os.getenv(env_key), "")
    if preferred and preferred in by_id and by_id[preferred]["locale"] == locale:
        return by_id[preferred]
    for row in catalog:
        if row["locale"] == locale:
            return row
    raise HTTPException(
        status_code=400,
        detail=(
            f"No Piper voice available for locale '{locale}'. "
            f"Install a matching English or Persian Piper model under {PIPER_MODELS_DIR}."
        ),
    )


@app.get("/health")
def health() -> dict:
    catalog = voice_catalog()
    voice_paths_ok = sum(
        1
        for v in catalog
        if os.path.isfile(v["path"]) and os.path.isfile(f"{v['path']}.json")
    )
    piper_ok = _piper_binary_ready(PIPER_BIN)
    onnx_ok = _piper_model_onnx_exists()
    json_ok = _piper_model_json_exists()
    tts_ok = _tts_stack_ready()
    rag_state = getattr(app.state, "rag", None) if hasattr(app, "state") else None
    return {
        "status": "ok",
        "mode": "offline",
        "service": "smart-avatar-backend",
        "modelBase": MODEL_API_BASE,
        "modelName": MODEL_NAME,
        "rag": rag_state,
        "ttsConfigured": tts_ok,
        "tts": {
            "piperExecutableOk": piper_ok,
            "piperBinRaw": PIPER_BIN_RAW,
            "piperBinResolved": PIPER_BIN,
            "modelOnnxFound": onnx_ok,
            "modelOnnxJsonFound": json_ok,
            "voiceCount": len(catalog),
            "voicesWithConfigOk": voice_paths_ok,
            "voicesWithMetaIssues": sum(1 for v in catalog if v.get("issues")),
            "modelsDir": PIPER_MODELS_DIR,
        },
    }


@app.get("/rag/status")
def rag_status() -> dict[str, Any]:
    try:
        from app.rag.config import load_rag_settings
        from app.rag.loader import load_faq_records
        from app.rag.service import get_rag_service
        from app.rag.store import index_ready

        settings = load_rag_settings()
        svc = get_rag_service()
        faq_count = 0
        if os.path.isfile(settings.faq_path):
            faq_count = len(load_faq_records(settings.faq_path))
        startup = getattr(app.state, "rag", None)
        return {
            "enabled": settings.enabled,
            "buildOnStartup": settings.build_on_startup,
            "indexReady": index_ready(settings.index_dir),
            "faqPath": settings.faq_path,
            "indexDir": settings.index_dir,
            "faqRecordCount": faq_count,
            "topK": settings.top_k,
            "minScore": settings.min_score,
            "embeddingModel": settings.embedding_model,
            "embeddingApiBase": settings.embedding_api_base,
            "embeddingConfigured": bool(
                settings.embedding_api_base and settings.embedding_api_key
            ),
            "startup": startup,
        }
    except Exception as error:
        return {"enabled": False, "error": str(error)[:400]}


@app.get("/config")
def app_config() -> dict[str, Any]:
    catalog = voice_catalog()
    voices = [
        {
            "id": v["id"],
            "label": v["label"],
            "locale": v["locale"],
            "configOk": len(v.get("issues", [])) == 0,
            "voiceAge": v.get("voiceAge", "young"),
        }
        for v in catalog
    ]
    return {
        "voices": voices,
        "modelName": MODEL_NAME,
        "avatarMapPath": VOICE_AVATAR_MAP_PATH,
    }


@app.post("/chat/respond", response_model=ChatResponse)
async def chat_respond(payload: ChatRequest) -> ChatResponse:
    request_started = time.perf_counter()
    locale: Literal["fa", "en"] = payload.locale
    speaking_speed: Literal["low", "medium", "high"] = payload.speakingSpeed
    face_age: Literal["child", "young", "old"] = payload.avatarFaceAge
    length_scale = _length_scale_for_speaking_speed(speaking_speed)
    base_system = SYSTEM_PROMPT_FA if locale == "fa" else SYSTEM_PROMPT_EN
    system_prompt = _system_prompt_with_length_cap(base_system, locale)
    escalation = ESCALATION_RESPONSE_FA if locale == "fa" else ESCALATION_RESPONSE_EN

    voice_entry = _resolve_voice_entry(locale, payload.voiceId)
    voice_path = str(voice_entry["path"])
    voice_label = str(voice_entry["label"])
    resolved_voice_id = str(voice_entry["id"])

    is_high_risk = _is_high_risk_text(payload.userText)
    model_attempts = 0
    llm_meta: dict[str, Any] = {}
    rag_meta: dict[str, Any] = {"enabled": False}

    try:
        model_started = time.perf_counter()
        if is_high_risk:
            assistant_text = escalation
            model_latency_ms = 0
        else:
            prompt_for_llm = system_prompt
            try:
                from app.rag.config import load_rag_settings
                from app.rag.service import get_rag_service

                rag_settings = load_rag_settings()
                if rag_settings.enabled:
                    rag_svc = get_rag_service()
                    rag_context, rag_meta = await asyncio.to_thread(
                        rag_svc.retrieve,
                        payload.userText,
                        locale=locale,
                    )
                    rag_meta["enabled"] = True
                    if rag_context:
                        prompt_for_llm = f"{system_prompt}\n\n{rag_context}"
            except Exception as rag_error:
                rag_meta = {
                    "enabled": True,
                    "error": str(rag_error)[:400],
                }
            assistant_text, model_attempts, llm_meta = await _call_llm(
                payload.userText, prompt_for_llm, locale=locale
            )
            model_latency_ms = int((time.perf_counter() - model_started) * 1000)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    diagnostic_rewrite_applied = _needs_diagnostic_safety_rewrite(assistant_text)
    if diagnostic_rewrite_applied:
        assistant_text = _safe_non_diagnostic_rewrite(assistant_text, locale)

    tts_text = _strip_for_tts(assistant_text)
    tts_was_sanitized = tts_text != (assistant_text or "").strip()
    if not tts_text:
        tts_text = _tts_fallback_line(locale)

    try:
        tts_started = time.perf_counter()
        audio_path, audio_file_path = _synthesize_with_piper(
            tts_text,
            voice_path,
            length_scale,
            int(voice_entry.get("numSpeakers") or 1),
            int(voice_entry.get("namedSpeakerCount") or 0),
        )
        tts_latency_ms = int((time.perf_counter() - tts_started) * 1000)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    duration_ms = _get_audio_duration_ms(audio_file_path)
    visemes = _build_viseme_timeline(tts_text, duration_ms)
    total_latency_ms = int((time.perf_counter() - request_started) * 1000)

    EVAL_STATS["requests"] += 1
    request_count = EVAL_STATS["requests"]
    if is_high_risk:
        EVAL_STATS["highRiskRequests"] += 1
    EVAL_STATS["avgModelMs"] = _update_running_average(
        EVAL_STATS["avgModelMs"], request_count, float(model_latency_ms)
    )
    EVAL_STATS["avgTtsMs"] = _update_running_average(
        EVAL_STATS["avgTtsMs"], request_count, float(tts_latency_ms)
    )
    EVAL_STATS["avgTotalMs"] = _update_running_average(
        EVAL_STATS["avgTotalMs"], request_count, float(total_latency_ms)
    )
    EVAL_STATS["avgAudioDurationMs"] = _update_running_average(
        EVAL_STATS["avgAudioDurationMs"], request_count, float(duration_ms)
    )

    return ChatResponse(
        assistantText=assistant_text,
        audioPath=audio_path,
        visemes=visemes,
        meta={
            "source": "smart-avatar-locale-voices",
            "sessionId": payload.sessionId,
            "model": MODEL_NAME,
            "locale": locale,
            "voiceId": resolved_voice_id,
            "voiceLabel": voice_label,
            "speakingSpeed": speaking_speed,
            "piperLengthScale": length_scale,
            "modelAttempts": model_attempts,
            "modelCompletion": llm_meta,
            "ttsSanitized": tts_was_sanitized,
            "durationMs": duration_ms,
            "avatar": {
                "voiceAge": str(voice_entry.get("voiceAge", "young")),
                "faceAge": face_age,
            },
            "rag": rag_meta,
            "latencyMs": {
                "model": model_latency_ms,
                "tts": tts_latency_ms,
                "total": total_latency_ms,
            },
            "safety": {
                "isHighRiskInput": is_high_risk,
                "diagnosticRewriteApplied": diagnostic_rewrite_applied,
            },
        },
    )


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return {
        "status": "ok",
        "mode": "offline",
        "metrics": EVAL_STATS,
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon_placeholder() -> Response:
    return Response(status_code=204)


if os.path.isdir(_UI_ROOT):
    app.mount("/", StaticFiles(directory=_UI_ROOT, html=True), name="ui")
