"""Load FAQ examples and build a high-priority conversational roadmap for the system prompt."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.paths import default_faq_path, resolve_path

_GENERIC_RESPONSE_RE = re.compile(
    r"^(می‌?فهم|می‌دون|می‌شنوم|من اینجام|ممنون که|خوشحالم که|طبیعی[‌ ]?ست|مهمه که)",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


@dataclass(frozen=True)
class FaqRecord:
    user: str
    responses: tuple[str, ...]
    category: str

    @classmethod
    def from_dict(cls, row: dict, index: int) -> FaqRecord:
        responses_raw = row.get("responses") or []
        if not isinstance(responses_raw, list):
            responses_raw = [str(responses_raw)]
        responses = tuple(str(r).strip() for r in responses_raw if str(r).strip())
        return cls(
            user=str(row.get("user", "")).strip(),
            responses=responses,
            category=str(row.get("category", "general")).strip() or "general",
        )


def faq_path() -> Path:
    raw = os.getenv("FAQ_PATH", "").strip() or os.getenv("RAG_FAQ_PATH", "").strip()
    if raw:
        return resolve_path(raw)
    return default_faq_path()


def load_faq_records(path: Path | None = None) -> list[FaqRecord]:
    target = path or faq_path()
    text = target.read_text(encoding="utf-8")
    data, _end = json.JSONDecoder().raw_decode(text.lstrip("\ufeff"))
    if not isinstance(data, list):
        raise ValueError(f"FAQ root must be a JSON array, got {type(data).__name__}")
    records: list[FaqRecord] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        rec = FaqRecord.from_dict(row, i)
        if rec.user:
            records.append(rec)
    return records


def _pick_example_response(responses: tuple[str, ...]) -> str:
    for response in responses:
        if "?" in response or "؟" in response:
            return response
    for response in responses:
        if not _GENERIC_RESPONSE_RE.search(response.strip()):
            return response
    return responses[0] if responses else ""


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 1}


def _score_record(user_text: str, record: FaqRecord) -> float:
    """Simple overlap score so closer FAQ rows float to the top of the roadmap."""
    query = _tokens(user_text)
    if not query:
        return 0.0
    hay = _tokens(f"{record.user} {record.category} {' '.join(record.responses)}")
    if not hay:
        return 0.0
    overlap = len(query & hay)
    return overlap / max(len(query), 1)


def build_guidance_context(
    *,
    locale: Literal["fa", "en"],
    user_text: str | None = None,
) -> str:
    if locale != "fa":
        return ""
    try:
        records = load_faq_records()
    except (OSError, ValueError):
        return ""
    if not records:
        return ""

    ranked = list(records)
    if user_text and user_text.strip():
        ranked.sort(key=lambda r: _score_record(user_text, r), reverse=True)

    intro = (
        "### نقشهٔ راه پاسخ (اولویت خیلی بالا — از faq_dataset)\n"
        "این نمونه‌ها سبک اصلی گفت‌وگو هستند، نه فقط الهام.\n"
        "قوانین:\n"
        "1) مثل همین نمونه‌ها کوتاه و مشخص حرف بزن — معمولاً یک سؤال شفاف برای جلو بردن گفتگو.\n"
        "2) اگر موضوع کاربر نزدیک یکی از این‌هاست، همان مسیر را ادامه بده (کاوش با سؤال، نه سخنرانی).\n"
        "3) همدلی بلند، نصیحت کلی، و لیست‌های طولانی ننویس.\n"
        "4) تشخیص نده؛ کپی لفظ‌به‌لفظ لازم نیست، ولی لحن و ساختار سؤال‌محور را حفظ کن.\n"
        "نمونه‌ها (نزدیک‌ترین‌ها اول):"
    )
    lines = [intro]
    by_category: dict[str, list[str]] = {}
    for rec in ranked:
        example = _pick_example_response(rec.responses)
        if not example:
            continue
        by_category.setdefault(rec.category, []).append(f"«{rec.user}» → «{example}»")

    # Prefer ranked order overall, but group labels help the model treat it as a map
    seen_cats: list[str] = []
    for rec in ranked:
        if rec.category not in seen_cats and rec.category in by_category:
            seen_cats.append(rec.category)

    for cat in seen_cats:
        lines.append(f"[{cat}]")
        for item in by_category[cat]:
            lines.append(f"- {item}")
    return "\n".join(lines)


def get_guidance_context(
    locale: Literal["fa", "en"],
    user_text: str | None = None,
) -> str:
    # Ranked by user_text — do not cache the ranked variant
    if user_text and user_text.strip():
        return build_guidance_context(locale=locale, user_text=user_text)
    return _cached_guidance_context(locale)


@lru_cache(maxsize=2)
def _cached_guidance_context(locale: Literal["fa", "en"]) -> str:
    return build_guidance_context(locale=locale, user_text=None)


def reload_guidance_cache() -> None:
    _cached_guidance_context.cache_clear()
