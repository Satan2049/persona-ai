from .types import FaqRecord, IndexedChunk


def chunk_faq_records(records: list[FaqRecord]) -> list[IndexedChunk]:
    chunks: list[IndexedChunk] = []
    for rec in records:
        embed_text = f"user: {rec.user}\ncategory: {rec.category}"
        chunks.append(IndexedChunk(record=rec, embed_text=embed_text))
    return chunks
