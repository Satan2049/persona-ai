from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FaqRecord:
    id: str
    user: str
    responses: tuple[str, ...]
    category: str

    @classmethod
    def from_dict(cls, row: dict[str, Any], index: int) -> "FaqRecord":
        responses_raw = row.get("responses") or []
        if not isinstance(responses_raw, list):
            responses_raw = [str(responses_raw)]
        responses = tuple(str(r).strip() for r in responses_raw if str(r).strip())
        return cls(
            id=f"faq-{index}",
            user=str(row.get("user", "")).strip(),
            responses=responses,
            category=str(row.get("category", "general")).strip() or "general",
        )


@dataclass(frozen=True)
class IndexedChunk:
    record: FaqRecord
    embed_text: str


@dataclass(frozen=True)
class RetrievedHit:
    record: FaqRecord
    score: float
