from pydantic import BaseModel, Field
from typing import Optional, List
from app.db import search_vector_db
from app.openai import get_embedding
import numpy as np
from numpy.linalg import norm

class QueryKnowledgeBaseTool(BaseModel):
    query_input: str = Field(..., description="User query")
    query_category: Optional[str] = Field(None)
    price_min: Optional[float] = Field(None)
    price_max: Optional[float] = Field(None)
    price_tolerance: Optional[float] = Field(500_000)
    brand: Optional[str] = Field(None)
    feature_keywords: Optional[List[str]] = Field(None)
    size_preferences: Optional[List[str]] = Field(None)

    async def __call__(self, rdb):
        query_vector = await get_embedding(self.query_input)
        filters = []

        if self.query_category:
            filters.append(f'@category:"{self.query_category.lower()}"')
        if self.brand:
            filters.append(f'@brand:"{self.brand.lower()}"')
        if self.feature_keywords:
            kw_filter = ' | '.join([f'@features_flat:{{{k.lower()}}}' for k in self.feature_keywords])
            filters.append(f'({kw_filter})')
        if self.size_preferences:
            size_filter = ' | '.join([f'@sizes_flat:{{{s.upper()}}}' for s in self.size_preferences])
            filters.append(f'({size_filter})')
        if self.price_min or self.price_max:
            min_p = self.price_min - self.price_tolerance if self.price_min else '-inf'
            max_p = self.price_max + self.price_tolerance if self.price_max else '+inf'
            filters.append(f'@price_numeric:[{min_p} {max_p}]')

        results = await search_vector_db(rdb, query_vector, top_k=10, filters=filters)

        if not results:
            return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

        # Rank اضافی اگر نیاز (semantic score already in query)
        top_results = sorted(results, key=lambda x: x['score'], reverse=True)
        output = []
        for i, chunk in enumerate(top_results):
            meta = chunk.get("metadata", {})
            name = meta.get("name", "بدون نام")
            price = meta.get("price", "نامشخص")
            link = meta.get("link", "")
            image = meta.get("image", "")
            stock_note = ""
            variations = meta.get("variations", [])
            if isinstance(variations, list):
                low_stock = any(int(v.get("stock", "0")) < 5 for v in variations if v.get("stock", "").isdigit())
                if low_stock:
                    stock_note = "⚠️ موجودی محدود (کمتر از ۵ عدد)!"
            sizes = [v.get("size", "") for v in variations if v.get("size")]
            features = meta.get("features_flat", "")

            block = (
                f"{i+1}. **{name}**\n"
                f"💰 قیمت: {price}\n"
                f"{stock_note}\n"
                f"📏 سایزها: {', '.join(sizes)}\n"
                f"🔍 ویژگی‌ها: {features}\n"
                f"🖼️ تصویر: {image}\n"
                f"🔗 [مشاهده محصول]({link})\n"
            )
            output.append(block)

        return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"