import json
from pathlib import Path

import numpy as np

from .types import FaqRecord


META_FILE = "meta.jsonl"
VECTORS_FILE = "vectors.npy"


def write_index(index_dir: str | Path, records: list[FaqRecord], vectors: np.ndarray) -> None:
    root = Path(index_dir)
    root.mkdir(parents=True, exist_ok=True)
    meta_path = root / META_FILE
    with meta_path.open("w", encoding="utf-8") as handle:
        for rec in records:
            line = {
                "id": rec.id,
                "user": rec.user,
                "responses": list(rec.responses),
                "category": rec.category,
            }
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
    np.save(root / VECTORS_FILE, vectors.astype(np.float32))


def load_index(index_dir: str | Path) -> tuple[list[FaqRecord], np.ndarray]:
    root = Path(index_dir)
    meta_path = root / META_FILE
    vec_path = root / VECTORS_FILE
    if not meta_path.is_file() or not vec_path.is_file():
        raise FileNotFoundError(
            f"RAG index missing under {root}. Run: python scripts/build_rag_index.py"
        )
    records: list[FaqRecord] = []
    with meta_path.open(encoding="utf-8") as handle:
        for i, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            records.append(FaqRecord.from_dict(row, i))
    vectors = np.load(vec_path)
    if vectors.shape[0] != len(records):
        raise ValueError("vectors.npy row count does not match meta.jsonl")
    return records, vectors


def index_ready(index_dir: str | Path) -> bool:
    root = Path(index_dir)
    return (root / META_FILE).is_file() and (root / VECTORS_FILE).is_file()
