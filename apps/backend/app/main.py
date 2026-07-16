import asyncio
import json
import logging
import os
import re
import time
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import rhubarb, stt, tts
from app.paths import (
    app_data_dir,
    default_ui_root,
    default_voice_avatar_map,
    ensure_app_data_dirs,
    env_path_anchor,
    find_dev_backend_env_file,
    load_application_env,
    loaded_env_files,
    resolve_path,
)

_BACKEND_DIR = str(env_path_anchor())
load_application_env()
ensure_app_data_dirs()
tts.reload_tts_config()
stt.reload_stt_config()
rhubarb.reload_rhubarb_config()
_dev_env = find_dev_backend_env_file()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="Smart Avatar Offline Backend",
    version="1.3.2",
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


def _resolve_path_from_backend_dir(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    return str(resolve_path(text, base=Path(_BACKEND_DIR)))


VOICE_AVATAR_MAP_PATH = (
    _resolve_path_from_backend_dir(os.getenv("VOICE_AVATAR_MAP_PATH", ""))
    or str(default_voice_avatar_map())
)

_voice_avatar_map_cache: dict[str, Any] | None = None


def reload_runtime_config() -> None:
    """Re-read environment after Settings UI saves AppData .env."""
    global MODEL_API_BASE, MODEL_API_KEY, MODEL_NAME, MODEL_TIMEOUT_SECONDS
    global MODEL_MAX_RETRIES, MODEL_TEMPERATURE, MODEL_MAX_TOKENS
    global SOCIAL_EMERGENCY_NUMBER, RESEARCHER_NUMBER
    global VOICE_AVATAR_MAP_PATH, _voice_avatar_map_cache
    global _BACKEND_DIR, _dev_env

    load_application_env()
    _BACKEND_DIR = str(env_path_anchor())
    _dev_env = find_dev_backend_env_file()
    MODEL_API_BASE = os.getenv("MODEL_API_BASE", "http://127.0.0.1:11434/v1")
    MODEL_API_KEY = os.getenv("MODEL_API_KEY", "local-key")
    MODEL_NAME = os.getenv("MODEL_NAME", "iranian-model")
    MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "25"))
    MODEL_MAX_RETRIES = int(os.getenv("MODEL_MAX_RETRIES", "3"))
    MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.5"))
    MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "380"))
    SOCIAL_EMERGENCY_NUMBER = _env_trim(os.getenv("SOCIAL_EMERGENCY_NUMBER"), "123")
    RESEARCHER_NUMBER = _env_trim(os.getenv("RESEARCHER_NUMBER"), "09373759943")
    VOICE_AVATAR_MAP_PATH = (
        _resolve_path_from_backend_dir(os.getenv("VOICE_AVATAR_MAP_PATH", ""))
        or str(default_voice_avatar_map())
    )
    tts.reload_tts_config()
    stt.reload_stt_config()
    rhubarb.reload_rhubarb_config()
    _voice_avatar_map_cache = None


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


_UI_ROOT = str(default_ui_root())

SYSTEM_PROMPT_FA = (
    "You are a supportive psychological guidance assistant for Iranian users. "
    "Always reply in Persian (Farsi) using Persian script. "
    "Do not use Arabic script or Arabic dialect; do not switch to English unless the user explicitly asks for English. "
    "PRIMARY STYLE (highest priority): follow the FAQ conversational roadmap when it is attached — "
    "short, focused clarifying questions that gently explore what the user said, "
    "like a step-by-step guide rather than a lecture or long empathy speech. "
    "If the user's topic matches a FAQ example, stay on that path (probe with one clear question). "
    "Be warm and practical, but keep the FAQ question-led structure first. "
    "Vary wording; do not diagnose. "
    "Do NOT give phone numbers or contact lines in normal conversation. "
    "Only mention emergency or researcher numbers if the user explicitly asks how to reach help "
    "or describes immediate self-harm or suicide intent. "
    "Keep every reply short: about 1–3 sentences unless the user explicitly asks for more. "
    "Prefer ending with a single clear question. No long essays or numbered lists."
)

SYSTEM_PROMPT_EN = (
    "You are a supportive psychological guidance assistant. "
    "Always reply in clear English only. Do not use Persian or other languages unless the user explicitly asks to switch. "
    "Be warm, conversational, and practical — like a thoughtful counselor in chat, not a formal brochure. "
    "Vary your openings and phrasing; avoid repeating the same empathy formulas in every reply. "
    "Do not diagnose. "
    "Do NOT give phone numbers or contact lines in normal conversation. "
    "Only mention emergency or researcher numbers if the user explicitly asks how to reach help "
    "or describes immediate self-harm or suicide intent. "
    "Keep every reply short: about 2–5 sentences unless the user explicitly asks for more. "
    "No long essays or numbered lists."
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

CONTACT_REQUEST_TERMS = [
    "شماره",
    "تماس",
    "تلفن",
    "پژوهشگر",
    "اورژانس",
    "number",
    "contact",
    "call",
    "phone",
    "reach",
    "hotline",
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
    """Remove emoji, markdown, and common stage directions for natural speech."""
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


def _http_status_should_retry(status: int) -> bool:
    if status in (408, 429):
        return True
    return 500 <= status <= 599

app.mount("/audio", StaticFiles(directory=tts.AUDIO_OUTPUT_DIR), name="audio")


class ChatRequest(BaseModel):
    sessionId: str = Field(min_length=1)
    userText: str = Field(min_length=1)
    emotionHint: str | None = None
    locale: Literal["fa", "en"] = "fa"
    voiceId: str | None = Field(default=None, description="OpenAI-compatible TTS voice id")
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
    "avgRhubarbMs": 0.0,
    "avgTotalMs": 0.0,
    "avgAudioDurationMs": 0.0,
}


def _visemes_from_rows(rows: list[dict[str, Any]]) -> list[VisemeItem]:
    return [
        VisemeItem(
            startMs=int(row["startMs"]),
            endMs=int(row["endMs"]),
            viseme=str(row["viseme"]),
            weight=float(row["weight"]),
        )
        for row in rows
    ]


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


def _user_wants_contact_info(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in CONTACT_REQUEST_TERMS)


def _strip_unwanted_contact_mentions(text: str) -> str:
    """Remove configured contact numbers when the model adds them without cause."""
    if not text:
        return text
    numbers = {SOCIAL_EMERGENCY_NUMBER, RESEARCHER_NUMBER}
    sentences = re.split(r"(?<=[.!?؟۔…؛])\s+", text.strip())
    kept: list[str] = []
    for sentence in sentences:
        if not sentence.strip():
            continue
        if any(number in sentence for number in numbers if number):
            continue
        kept.append(sentence.strip())
    cleaned = " ".join(kept).strip()
    return cleaned or text.strip()


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
        raise RuntimeError(f"Model API error — HTTP {response.status_code}: {detail}")
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
    try:
        entry = tts.resolve_voice_entry(locale, voice_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    row = dict(entry)
    row["voiceAge"] = _voice_age_for_voice_id(str(row["id"]))
    return row


def _tts_config_suspicious() -> bool:
    base = (tts.TTS_API_BASE or "").lower()
    local = "127.0.0.1" in base or "localhost" in base
    key = (tts.TTS_API_KEY or "").strip()
    return not local and key in ("", "local-key", "api-key")


def _stt_config_suspicious() -> bool:
    base = (stt.STT_API_BASE or "").lower()
    local = "127.0.0.1" in base or "localhost" in base
    key = (stt.STT_API_KEY or "").strip()
    return not local and key in ("", "local-key", "api-key")


def _mask_api_key(key: str) -> str:
    text = (key or "").strip()
    if not text or text in ("local-key", "api-key"):
        return "(default placeholder — set MODEL_API_KEY)"
    if len(text) <= 10:
        return text[:3] + "…"
    return f"{text[:8]}…{text[-4:]}"


def _llm_config_suspicious() -> bool:
    base = (MODEL_API_BASE or "").lower()
    local = "127.0.0.1" in base or "localhost" in base
    key = (MODEL_API_KEY or "").strip()
    return not local and key in ("", "local-key", "api-key")


@app.get("/health")
def health() -> dict:
    catalog = tts.voice_catalog()
    tts_ok = tts.tts_stack_ready()
    guidance_count = 0
    try:
        from app.guidance import load_faq_records

        guidance_count = len(load_faq_records())
    except (OSError, ValueError):
        pass
    status = tts.tts_status()
    stt_ok = stt.stt_stack_ready()
    stt_status = stt.stt_status()
    return {
        "status": "ok",
        "mode": "offline",
        "service": "smart-avatar-backend",
        "modelBase": MODEL_API_BASE,
        "modelName": MODEL_NAME,
        "envSource": str(_dev_env) if _dev_env and _dev_env.is_file() else str(app_data_dir() / ".env"),
        "envFilesLoaded": [str(path) for path in loaded_env_files()],
        "personaBuildId": os.getenv("PERSONA_BUILD_ID", "").strip(),
        "modelApiKeyHint": _mask_api_key(MODEL_API_KEY),
        "llmConfigSuspicious": _llm_config_suspicious(),
        "ttsConfigSuspicious": _tts_config_suspicious(),
        "sttConfigSuspicious": _stt_config_suspicious(),
        "guidanceExamples": guidance_count,
        "ttsConfigured": tts_ok,
        "sttConfigured": stt_ok,
        "rhubarbConfigured": rhubarb.rhubarb_ready(),
        "tts": {
            **status,
            "voiceCount": len(catalog),
            "ttsApiKeyHint": _mask_api_key(tts.TTS_API_KEY),
        },
        "stt": {
            **stt_status,
            "sttApiKeyHint": _mask_api_key(stt.STT_API_KEY),
        },
        "rhubarb": rhubarb.rhubarb_status(),
    }


class TranscribeResponse(BaseModel):
    text: str
    locale: Literal["fa", "en"]
    provider: str = "openai-compatible"


@app.post("/chat/transcribe", response_model=TranscribeResponse)
async def chat_transcribe(
    file: UploadFile = File(...),
    locale: Literal["fa", "en"] = Form("fa"),
) -> TranscribeResponse:
    try:
        audio_bytes = await file.read()
        text = await stt.transcribe_audio(
            audio_bytes,
            filename=file.filename or "speech.webm",
            content_type=file.content_type,
            locale=locale,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return TranscribeResponse(text=text, locale=locale)


@app.get("/config")
def app_config() -> dict[str, Any]:
    catalog = tts.voice_catalog()
    voices = [
        {
            "id": v["id"],
            "label": v["label"],
            "locale": "any",
            "configOk": True,
            "voiceAge": _voice_age_for_voice_id(str(v["id"])),
            "gender": str(v.get("gender") or "female"),
        }
        for v in catalog
    ]
    return {
        "voices": voices,
        "modelName": MODEL_NAME,
        "avatarMapPath": VOICE_AVATAR_MAP_PATH,
    }


class SettingsUpdateRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


@app.get("/settings")
def get_settings() -> dict[str, Any]:
    from app.settings_store import get_snapshot

    return get_snapshot()


@app.put("/settings")
def put_settings(payload: SettingsUpdateRequest) -> dict[str, Any]:
    from app.settings_store import get_snapshot

    snapshot = get_snapshot()
    snapshot["savedKeys"] = []
    return snapshot


@app.post("/chat/respond", response_model=ChatResponse)
async def chat_respond(payload: ChatRequest) -> ChatResponse:
    request_started = time.perf_counter()
    locale: Literal["fa", "en"] = payload.locale
    speaking_speed: Literal["low", "medium", "high"] = payload.speakingSpeed
    face_age: Literal["child", "young", "old"] = payload.avatarFaceAge
    base_system = SYSTEM_PROMPT_FA if locale == "fa" else SYSTEM_PROMPT_EN
    system_prompt = _system_prompt_with_length_cap(base_system, locale)
    escalation = ESCALATION_RESPONSE_FA if locale == "fa" else ESCALATION_RESPONSE_EN

    voice_entry = _resolve_voice_entry(locale, payload.voiceId)
    voice_label = str(voice_entry["label"])
    resolved_voice_id = str(voice_entry["id"])

    is_high_risk = _is_high_risk_text(payload.userText)
    user_wants_contact = _user_wants_contact_info(payload.userText)
    model_attempts = 0
    llm_meta: dict[str, Any] = {}

    try:
        model_started = time.perf_counter()
        if is_high_risk:
            assistant_text = escalation
            model_latency_ms = 0
        else:
            from app.guidance import get_guidance_context

            guidance_context = get_guidance_context(locale, payload.userText)
            # Put the FAQ roadmap first so the model treats it as the primary guide
            prompt_for_llm = (
                f"{guidance_context}\n\n{system_prompt}"
                if guidance_context
                else system_prompt
            )
            assistant_text, model_attempts, llm_meta = await _call_llm(
                payload.userText, prompt_for_llm, locale=locale
            )
            if not is_high_risk and not user_wants_contact:
                assistant_text = _strip_unwanted_contact_mentions(assistant_text)
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
        audio_path, audio_file_path, duration_ms = await tts.synthesize_speech(
            tts_text,
            resolved_voice_id,
            speaking_speed,
        )
        tts_latency_ms = int((time.perf_counter() - tts_started) * 1000)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    rhubarb_started = time.perf_counter()
    viseme_rows, rhubarb_meta = await rhubarb.analyze_wav(
        audio_file_path,
        duration_ms=duration_ms,
        dialog_text=tts_text,
        locale=locale,
    )
    rhubarb_latency_ms = int((time.perf_counter() - rhubarb_started) * 1000)
    if rhubarb_meta.get("latencyMs"):
        rhubarb_latency_ms = int(rhubarb_meta["latencyMs"])
    visemes = _visemes_from_rows(viseme_rows)
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
    EVAL_STATS["avgRhubarbMs"] = _update_running_average(
        EVAL_STATS["avgRhubarbMs"], request_count, float(rhubarb_latency_ms)
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
            "ttsModel": tts.TTS_MODEL,
            "modelAttempts": model_attempts,
            "modelCompletion": llm_meta,
            "ttsSanitized": tts_was_sanitized,
            "durationMs": duration_ms,
            "lipSync": {
                **rhubarb_meta,
                "latencyMs": rhubarb_latency_ms,
            },
            "avatar": {
                "voiceAge": str(voice_entry.get("voiceAge", "young")),
                "faceAge": face_age,
            },
            "latencyMs": {
                "model": model_latency_ms,
                "tts": tts_latency_ms,
                "rhubarb": rhubarb_latency_ms,
                "total": total_latency_ms,
            },
            "safety": {
                "isHighRiskInput": is_high_risk,
                "contactInfoRequested": user_wants_contact,
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
