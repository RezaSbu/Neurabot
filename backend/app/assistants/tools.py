from pydantic import BaseModel, Field
from app.db import search_vector_db, get_all_vectors
from app.openai import get_embedding
import numpy as np
from numpy.linalg import norm

class QueryKnowledgeBaseTool(BaseModel):
    """Query and filter knowledge base for product search."""
    query_input: str = Field(description='User search query about motorcycle products')

    async def __call__(self, rdb):
        query_vector = await get_embedding(self.query_input)
        all_chunks = await get_all_vectors(rdb)

        q = self.query_input.lower().strip()
        query_words = set(q.split())

        # جستجوی تطبیقی قوی‌تر
        filtered_chunks = []
        for chunk in all_chunks:
            meta = chunk.get("metadata", {})
            text_fields = [
                chunk.get("text", ""),
                meta.get("name", ""),
                meta.get("brand", ""),
                meta.get("category", ""),
                meta.get("search_text", "")
            ]
            combined = " ".join(text_fields).lower()
            if any(word in combined for word in query_words):
                filtered_chunks.append(chunk)

        # fallback اگه خیلی کم بود
        if len(filtered_chunks) < 3:
            filtered_chunks = all_chunks

        vectors = [c["vector"] for c in filtered_chunks]
        texts = [c["text"] for c in filtered_chunks]
        doc_names = [c["doc_name"] for c in filtered_chunks]

        scores = []
        for idx, v in enumerate(vectors):
            try:
                sim = np.dot(query_vector, v) / (norm(query_vector) * norm(v))
            except:
                sim = 0
            scores.append((sim, idx))

        # top-k نهایی
        top_k = sorted(scores, reverse=True)[:5]
        results = []
        for score, idx in top_k:
            results.append(f"SOURCE: {doc_names[idx]}\n\"\"\"\n{texts[idx]}\n\"\"\"")

        return "\n\n---\n\n".join(results) + "\n\n---"

