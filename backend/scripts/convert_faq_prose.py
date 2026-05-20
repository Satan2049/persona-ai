#!/usr/bin/env python3
"""One-off: merge valid JSON FAQ rows and convert trailing prose to JSON; dedupe by user text."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
FAQ_PATH = _REPO / "data" / "faq_dataset.json"

_USER_MARKERS = ("جمله فرد:", "جمله فرد：")
_AVATAR_MARKERS = ("آواتار:", "اواتار:", "آواتار：")


def _strip_wrapping_quotes(text: str) -> str:
    t = text.strip()
    while t and t[0] in "\"'\u00ab\u201c":
        t = t[1:].lstrip()
    while t and t[-1] in "\"'\u00bb\u201d.,\u061f!":
        t = t[:-1].rstrip()
    return t


def _normalize_user(text: str) -> str:
    t = _strip_wrapping_quotes(text.strip())
    t = re.sub(r"\s+", " ", t)
    return t


def _normalize_response(text: str) -> str:
    t = _strip_wrapping_quotes(text.strip())
    if t.startswith("چالشی ملایم:"):
        t = t.split(":", 1)[1].strip()
    return t


def infer_category(user: str) -> str:
    u = user
    relationship_kw = (
        "رابطه",
        "تنها",
        "تنهایی",
        "طرد",
        "ولم",
        "دوست",
        "پیام",
        "نزدیک",
        "ترک",
        "وابسته",
        "مهم نیست",
        "پذیرفته",
        "جواب",
        "سرد",
        "متنفر",
        "پایدار",
        "منتقد",
    )
    identity_kw = (
        "کی هستم",
        "هویت",
        "خودم",
        "پوچ",
        "ارزش",
        "نقش",
        "شناس",
        "خواست",
        "ثابت",
        "واقعی",
        "خالی",
    )
    distress_kw = (
        "امید",
        "بمیر",
        "ناامید",
        "خسته شدم",
        "درد",
        "آسیب",
        "ناپدید",
        "تحمل",
        "بی‌ارزش",
        "معنا",
        "بیدار",
        "فرار",
        "آینده",
        "تموم",
        "خودکشی",
        "نبودنم",
        "جنگیدن",
    )
    emotion_kw = (
        "حالم",
        "احساسات",
        "خشم",
        "غم",
        "گریه",
        "بالا و پایین",
        "نوسان",
        "بی‌ثبات",
        "عصبانی",
        "خلق",
        "حس ",
    )
    if any(k in u for k in relationship_kw):
        return "relationship"
    if any(k in u for k in identity_kw):
        return "identity"
    if any(k in u for k in distress_kw):
        return "distress"
    if any(k in u for k in emotion_kw):
        return "emotion"
    return "impulsivity"


def parse_prose_block(text: str) -> list[dict]:
    records: list[dict] = []
    current_user: str | None = None
    current_responses: list[str] = []
    current_category: str | None = None

    def flush() -> None:
        nonlocal current_user, current_responses, current_category
        if not current_user:
            current_responses = []
            return
        responses = [_normalize_response(r) for r in current_responses if _normalize_response(r)]
        if responses:
            cat = current_category or infer_category(current_user)
            records.append(
                {
                    "user": current_user,
                    "responses": responses[:3],
                    "category": cat,
                }
            )
        current_user = None
        current_responses = []
        current_category = None

    lines = text.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("---"):
            continue

        user_hit = None
        for marker in _USER_MARKERS:
            if marker in line:
                idx = line.index(marker)
                user_hit = line[idx + len(marker) :].strip()
                break
        if user_hit is not None:
            flush()
            current_user = _normalize_user(user_hit)
            continue

        avatar_hit = None
        for marker in _AVATAR_MARKERS:
            if line.startswith(marker):
                avatar_hit = line[len(marker) :].strip()
                break
        if avatar_hit is not None:
            if avatar_hit:
                current_responses.append(avatar_hit)
            continue

        if current_user and line.startswith(("\u00ab", "\"")):
            current_responses.append(line)
            continue

    flush()
    return records


def load_json_array(text: str) -> list[dict]:
    data, _end = json.JSONDecoder().raw_decode(text.lstrip("\ufeff"))
    if not isinstance(data, list):
        raise ValueError("FAQ root must be a JSON array")
    out: list[dict] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        user = _normalize_user(str(row.get("user", "")))
        if not user:
            continue
        responses_raw = row.get("responses") or []
        if not isinstance(responses_raw, list):
            responses_raw = [responses_raw]
        responses = [_normalize_response(str(r)) for r in responses_raw if str(r).strip()]
        cat = str(row.get("category", "")).strip() or infer_category(user)
        out.append({"user": user, "responses": responses[:3], "category": cat})
    return out


def merge_dedupe(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for row in rows:
        key = _normalize_user(row["user"])
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def main() -> int:
    text = FAQ_PATH.read_text(encoding="utf-8")
    try:
        data, end = json.JSONDecoder().raw_decode(text.lstrip("\ufeff"))
        json_rows = load_json_array(text) if isinstance(data, list) else []
    except json.JSONDecodeError:
        json_rows = []
        end = 0

    prose = text[end:].strip()
    prose_rows = parse_prose_block(prose) if prose else []

    all_rows = merge_dedupe(json_rows + prose_rows)
    FAQ_PATH.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_rows)} FAQ records to {FAQ_PATH}")
    print(f"  from JSON array: {len(json_rows)}")
    print(f"  from prose: {len(prose_rows)}")
    print(f"  duplicates removed: {len(json_rows) + len(prose_rows) - len(all_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
