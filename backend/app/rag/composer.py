from typing import Literal

from .types import RetrievedHit


def compose_rag_context(
    hits: list[RetrievedHit],
    *,
    locale: Literal["fa", "en"],
) -> str:
    if not hits:
        return ""
    intro_fa = (
        "--- راهنمای بازیابی‌شده (فقط برای لحن و سبک؛ تشخیص نده، متن را کپی نکن) ---"
    )
    intro_en = (
        "--- Retrieved guidance (style reference only; do not diagnose or copy verbatim) ---"
    )
    lines = [intro_fa if locale == "fa" else intro_en]
    for i, hit in enumerate(hits, start=1):
        examples = " | ".join(hit.record.responses)
        lines.append(
            f"[{i}] category={hit.record.category} (score={hit.score:.2f})\n"
            f"User said: {hit.record.user}\n"
            f"Example responses: {examples}"
        )
    lines.append("---")
    return "\n".join(lines)
