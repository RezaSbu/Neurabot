from pydantic import BaseModel, Field
from typing import Optional, List
from app.db import search_vector_db
from app.openai import get_embedding
import numpy as np

class QueryKnowledgeBaseTool(BaseModel):
    query_input: str = Field(..., description="User query")
    query_category: Optional[str] = Field(None)
    price_min: Optional[float] = Field(None)
    price_max: Optional[float] = Field(None)
    price_tolerance: Optional[float] = Field(500_000)
    brand: Optional[str] = Field(None)
    feature_keywords: Optional[List[str]] = Field(None)
    size_preferences: Optional[List[str]] = Field(None)
    top_k: int = 10

    async def __call__(self, rdb):
        query_vector = await get_embedding(self.query_input)
        results = await search_vector_db(rdb, query_vector, top_k=self.top_k)

        if not results:
            return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

        output = []
        for i, chunk in enumerate(results):
            name = chunk.get("text", "بدون نام")
            doc = chunk.get("doc_name", "")
            score = round(chunk.get("score", 0) * 100, 2)
            chunk_id = chunk.get("chunk_id", "")

            block = (
                f"{i+1}. **{name}**\n"
                f"📄 سند: {doc}\n"
                f"📌 بخش: {chunk_id}\n"
                f"🔎 شباهت: {score}%\n"
            )
            output.append(block)

        return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"
