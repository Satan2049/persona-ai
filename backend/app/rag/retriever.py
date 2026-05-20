import numpy as np

from .types import FaqRecord, RetrievedHit


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


def search(
    query_vector: list[float],
    records: list[FaqRecord],
    vectors: np.ndarray,
    *,
    top_k: int,
    min_score: float,
) -> list[RetrievedHit]:
    if not records:
        return []
    q = np.array(query_vector, dtype=np.float32)
    qn = q / (np.linalg.norm(q) or 1.0)
    vn = _normalize(vectors.astype(np.float32))
    scores = vn @ qn
    order = np.argsort(scores)[::-1]
    hits: list[RetrievedHit] = []
    for idx in order[:top_k]:
        score = float(scores[idx])
        if score < min_score:
            break
        hits.append(RetrievedHit(record=records[int(idx)], score=score))
    return hits
