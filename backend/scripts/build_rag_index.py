#!/usr/bin/env python3
"""Build FAQ vector index for RAG. Requires EMBEDDING_API_KEY in backend/.env."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.rag.bootstrap import build_faq_index  # noqa: E402
from app.rag.config import load_rag_settings  # noqa: E402
from app.rag.loader import load_faq_records  # noqa: E402
from app.rag.store import index_ready  # noqa: E402


def main() -> int:
    settings = load_rag_settings()
    faq_path = Path(settings.faq_path)
    if not faq_path.is_file():
        print(f"FAQ file not found: {faq_path}", file=sys.stderr)
        return 1

    records = load_faq_records(faq_path)
    if not records:
        print("No FAQ records loaded.", file=sys.stderr)
        return 1

    print(f"Loaded {len(records)} FAQ records from {faq_path}")
    print(f"Embedding with model={settings.embedding_model!r} ...")
    try:
        count = build_faq_index(settings)
    except Exception as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1

    out = Path(settings.index_dir)
    print(f"Wrote {out / 'meta.jsonl'}")
    print(f"Wrote {out / 'vectors.npy'}  records={count}")
    return 0 if index_ready(settings.index_dir) else 1


if __name__ == "__main__":
    raise SystemExit(main())
