from pydantic import BaseModel, Field
from typing import Optional, List
from app.db import get_all_vectors
from app.openai import get_embedding
import numpy as np
from numpy.linalg import norm

class QueryKnowledgeBaseTool(BaseModel):
    query_input: str = Field(..., description="User query")
    query_category: Optional[str] = Field(None)
    price_min: Optional[float] = Field(None)
    price_max: Optional[float] = Field(None)
    price_tolerance: Optional[float] = Field(0.05)  # 5% tolerance
    brand: Optional[str] = Field(None)
    feature_keywords: Optional[List[str]] = Field(None)
    size_preferences: Optional[List[str]] = Field(None)

    async def __call__(self, rdb):
        # 1) Embed the query
        query_vector = await get_embedding(self.query_input)

        # 2) Load all chunks
        all_chunks = await get_all_vectors(rdb)

        # Helper: strict match vs relaxed
        def matches_strict(chunk):
            meta = chunk["metadata"]
            if self.query_category and meta.get("category") != self.query_category:
                return False
            if self.brand and self.brand.lower() not in meta.get("brand", "").lower():
                return False
            if self.size_preferences:
                sizes = [v.get("size", "").upper() for v in meta.get("variations", [])]
                if not any(s in sizes for s in self.size_preferences):
                    return False
            if self.feature_keywords:
                feats = meta.get("features_flat", "").lower()
                if not any(k.lower() in feats for k in self.feature_keywords):
                    return False
            price = meta.get("price_numeric")
            if self.price_min is not None and price < self.price_min:
                return False
            if self.price_max is not None and price > self.price_max:
                return False
            return True

        def matches_relaxed(chunk):
            meta = chunk["metadata"]
            # category still mandatory
            if self.query_category and meta.get("category") != self.query_category:
                return False
            price = meta.get("price_numeric")
            if self.price_min is not None:
                if price < self.price_min * (1 - self.price_tolerance):
                    return False
            if self.price_max is not None:
                if price > self.price_max * (1 + self.price_tolerance):
                    return False
            # brand/features/size relaxed to any match
            brand_ok = True
            if self.brand:
                brand_ok = self.brand.lower() in meta.get("brand", "").lower()
            feats_ok = True
            if self.feature_keywords:
                feats_ok = any(k.lower() in meta.get("features_flat", "").lower()
                                for k in self.feature_keywords)
            size_ok = True
            if self.size_preferences:
                sizes = [v.get("size", "").upper() for v in meta.get("variations", [])]
                size_ok = any(s in sizes for s in self.size_preferences)
            return brand_ok or feats_ok or size_ok

        # Scoring function: weighted sum + embedding similarity
        def score(chunk):
            meta = chunk["metadata"]
            base = 0
            # weights: category highest
            if self.query_category and meta.get("category") == self.query_category:
                base += 5
            if self.brand and self.brand.lower() in meta.get("brand", "").lower():
                base += 3
            if self.feature_keywords and any(
                k.lower() in meta.get("features_flat", "").lower() for k in self.feature_keywords):
                base += 2
            if self.size_preferences:
                sizes = [v.get("size", "").upper() for v in meta.get("variations", [])]
                if any(s in sizes for s in self.size_preferences):
                    base += 1
            # similarity
            vec = chunk.get("vector", [])
            try:
                sim = np.dot(query_vector, vec) / (norm(query_vector) * norm(vec))
            except:
                sim = 0
            return base + sim

        # Phase 1: strict filtering
        strict_matches = [c for c in all_chunks if matches_strict(c)]
        strict_sorted = sorted(strict_matches, key=score, reverse=True)[:5]

        # Phase 2: relaxed ±5%
        remaining = [c for c in all_chunks if c not in strict_sorted]
        relaxed_matches = [c for c in remaining if matches_relaxed(c)]
        relaxed_sorted = sorted(relaxed_matches, key=score, reverse=True)[:5]

        # Format output
        def format_item(c):
            m = c["metadata"]
            stock_note = ""
            for v in m.get("variations", []):
                if isinstance(v.get("stock", ""), str) and v["stock"].startswith("1"):
                    stock_note = "⚠️ موجودی محدود!"
                    break
            return {
                "name": m.get("name"),
                "price": m.get("price"),
                "link": m.get("link"),
                "stock_note": stock_note,
                "sizes": [v.get("size") for v in m.get("variations", [])],
                "features": m.get("features_flat"),
                "image": m.get("image")
            }

        products = [format_item(c) for c in strict_sorted + relaxed_sorted]
        return {"products": products, "message": "این نتایج چطور بودند؟ 😊"}
