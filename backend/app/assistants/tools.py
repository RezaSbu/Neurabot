# filename: tools.py
from pydantic import BaseModel, Field
from typing import Optional, List
from app.db import get_qdrant_client, search_vector_db
from app.openai import get_embedding

class QueryKnowledgeBaseTool(BaseModel):
    query_input: str = Field(..., description="User query")
    query_category: Optional[str] = Field(None)
    price_min: Optional[float] = Field(None)
    price_max: Optional[float] = Field(None)
    price_tolerance: Optional[float] = Field(500_000)
    brand: Optional[str] = Field(None)
    feature_keywords: Optional[List[str]] = Field(None)
    size_preferences: Optional[List[str]] = Field(None)

    async def __call__(self, _):  # rdb not used anymore
        client = get_qdrant_client()
        query_vector = await get_embedding(self.query_input)

        # Build filters for hybrid search
        filters = {}
        if self.query_category:
            filters['metadata.category'] = self.query_category.lower()
        if self.brand:
            filters['metadata.brand'] = self.brand.lower()
        if self.price_min or self.price_max:
            price_filter = {}
            if self.price_min:
                price_filter['min'] = self.price_min - self.price_tolerance
            if self.price_max:
                price_filter['max'] = self.price_max + self.price_tolerance
            filters['metadata.price_numeric'] = price_filter
        if self.feature_keywords:
            filters['metadata.features_flat'] = {'contains_any': [k.lower() for k in self.feature_keywords]}
        if self.size_preferences:
            filters['metadata.sizes_flat'] = {'contains_any': [s.upper() for s in self.size_preferences]}

        results = await search_vector_db(client, query_vector, top_k=10, filters=filters)

        if not results:
            return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

        output = []
        for i, res in enumerate(results):
            meta = res.get('metadata', {})
            name = meta.get("name", "بدون نام")
            price = meta.get("price", "نامشخص")
            link = meta.get("link", "")
            image = meta.get("image", "")
            stock_note = ""
            variations = meta.get("variations", [])
            if isinstance(variations, list):
                for v in variations:
                    if v.get("stock", "").startswith("1"):
                        stock_note = "⚠️ موجودی محدود!"
                        break
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