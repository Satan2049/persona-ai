import json
from pathlib import Path
from typing import Any

from .types import FaqRecord


def load_faq_records(path: str | Path) -> list[FaqRecord]:
    """Load FAQ array from file; ignores trailing non-JSON prose after the first array."""
    text = Path(path).read_text(encoding="utf-8")
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
