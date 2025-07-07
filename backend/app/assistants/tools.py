from pydantic import BaseModel, Field
from typing import Optional
from app.db import get_all_vectors
from app.openai import get_embedding
import numpy as np
from numpy.linalg import norm

class QueryKnowledgeBaseTool(BaseModel):
    query_input: str = Field(..., description="User query")
    query_category: Optional[str] = Field(None, description="Category of product")
    price_min: Optional[float] = Field(None)
    price_max: Optional[float] = Field(None)
    brand: Optional[str] = Field(None)

    async def __call__(self, rdb):
        query_vector = await get_embedding(self.query_input)
        all_chunks = await get_all_vectors(rdb)

        filtered_chunks = []
        for chunk in all_chunks:
            meta = chunk.get("metadata", {})

            # فیلتر دسته
            if self.query_category and meta.get("category") != self.query_category:
                continue

            # فیلتر برند
            if self.brand and self.brand.lower() not in meta.get("brand", "").lower():
                continue

            # فیلتر قیمت
            price = meta.get("price_numeric", 0)
            if self.price_min and price < self.price_min:
                continue
            if self.price_max and price > self.price_max:
                continue

            filtered_chunks.append(chunk)

        # fallback در صورت کم بودن نتایج
        if len(filtered_chunks) < 3:
            filtered_chunks = all_chunks

        # محاسبه similarity
        scores = []
        for idx, c in enumerate(filtered_chunks):
            try:
                sim = np.dot(query_vector, c["vector"]) / (norm(query_vector) * norm(c["vector"]))
            except:
                sim = 0
            scores.append((sim, idx))

        # انتخاب top-5 نتیجه
        top_k = sorted(scores, reverse=True)[:5]
        results = []
        for score, idx in top_k:
            chunk = filtered_chunks[idx]
            meta = chunk.get("metadata", {})
            text_block = chunk['text']
            product_link = meta.get("link", "")
            product_name = meta.get("name", "محصول")

            results.append(
                f"SOURCE: {chunk['doc_name']}\n\"\"\"\n{text_block}\n\nلینک محصول: {product_link}\nنام محصول: {product_name}\n\"\"\""
            )

        return "\n\n---\n\n".join(results) + "\n\n---"
