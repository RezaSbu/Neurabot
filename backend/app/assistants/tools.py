# from pydantic import BaseModel, Field
# from typing import Optional, List
# from app.db import get_all_vectors
# from app.openai import get_embedding
# import numpy as np
# from numpy.linalg import norm

# class QueryKnowledgeBaseTool(BaseModel):
#     query_input: str = Field(..., description="User query")
#     query_category: Optional[str] = Field(None)
#     price_min: Optional[float] = Field(None)
#     price_max: Optional[float] = Field(None)
#     price_tolerance: Optional[float] = Field(500_000)
#     brand: Optional[str] = Field(None)
#     feature_keywords: Optional[List[str]] = Field(None)
#     size_preferences: Optional[List[str]] = Field(None)

#     async def __call__(self, rdb):
#         query_vector = await get_embedding(self.query_input)
#         all_chunks = await get_all_vectors(rdb)

#         scored_matches = []

#         for chunk in all_chunks:
#             meta = chunk.get("metadata", {})
#             price = meta.get("price_numeric", None)
#             if not isinstance(price, (int, float)):
#                 continue

#             brand = meta.get("brand", "").lower()
#             category = meta.get("category", "").lower()
#             name = meta.get("name", "").lower()
#             features = meta.get("features_flat", "").lower()
#             sizes = meta.get("sizes_flat", [])
#             variations = meta.get("variations", [])

#             score = 0
#             max_score = 0

#             if self.query_category:
#                 max_score += 1
#                 if self.query_category.lower() in category or self.query_category.lower() in name:
#                     score += 1

#             if self.brand:
#                 max_score += 1
#                 if self.brand.lower() in brand:
#                     score += 1

#             if self.feature_keywords:
#                 max_score += 1
#                 if any(k.lower() in features or k.lower() in name for k in self.feature_keywords):
#                     score += 1

#             if self.size_preferences and sizes:
#                 max_score += 1
#                 if any(s.upper() in sizes for s in self.size_preferences):
#                     score += 1

#             in_price = True
#             if self.price_min is not None and price < self.price_min:
#                 in_price = False
#             if self.price_max is not None and price > self.price_max + self.price_tolerance:
#                 in_price = False

#             near_price = False
#             if not in_price:
#                 if self.price_min and price >= self.price_min - self.price_tolerance:
#                     near_price = True
#                 if self.price_max and price <= self.price_max + self.price_tolerance:
#                     near_price = True

#             if self.price_min or self.price_max:
#                 max_score += 1
#                 if in_price or near_price:
#                     score += 1

#             if max_score == 0 or score >= max_score / 2:
#                 scored_matches.append((score, chunk))

#         if not scored_matches:
#             return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

#         def rank(chunks):
#             ranked = []
#             for score, chunk in chunks:
#                 try:
#                     sim = np.dot(query_vector, chunk["vector"]) / (norm(query_vector) * norm(chunk["vector"]))
#                 except:
#                     sim = 0
#                 final_score = score + sim
#                 ranked.append((final_score, chunk))
#             return [c for _, c in sorted(ranked, reverse=True)[:10]]

#         top_results = rank(scored_matches)
#         output = []
#         for i, chunk in enumerate(top_results):
#             meta = chunk.get("metadata", {})
#             name = meta.get("name", "بدون نام")
#             price = meta.get("price", "نامشخص")
#             link = meta.get("link", "")
#             image = meta.get("image", "")
#             stock_note = ""
#             variations = meta.get("variations", [])
#             if isinstance(variations, list):
#                 for v in variations:
#                     if v.get("stock", "").startswith("1"):
#                         stock_note = "⚠️ موجودی محدود!"
#                         break
#             sizes = [v.get("size", "") for v in variations if v.get("size")]
#             features = meta.get("features_flat", "")

#             block = (
#                 f"{i+1}. **{name}**\n"
#                 f"💰 قیمت: {price}\n"
#                 f"{stock_note}\n"
#                 f"📏 سایزها: {', '.join(sizes)}\n"
#                 f"🔍 ویژگی‌ها: {features}\n"
#                 f"🖼️ تصویر: {image}\n"
#                 f"🔗 [مشاهده محصول]({link})\n"
#             )
#             output.append(block)

#         return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"
    




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
    price_tolerance: Optional[float] = Field(500_000)
    brand: Optional[str] = Field(None)
    feature_keywords: Optional[List[str]] = Field(None)
    size_preferences: Optional[List[str]] = Field(None)

    async def __call__(self, rdb):
        query_vector = await get_embedding(self.query_input)
        all_chunks = await get_all_vectors(rdb)

        exact_matches = []
        near_matches = []

        for chunk in all_chunks:
            meta = chunk.get("metadata", {})
            price = meta.get("price_numeric", None)
            if not isinstance(price, (int, float)):
                continue

            brand = meta.get("brand", "").strip().lower()
            category = meta.get("category", "").strip().lower()
            name = meta.get("name", "").strip().lower()
            features = meta.get("features_flat", "").lower()
            sizes = meta.get("sizes_flat", [])
            variations = meta.get("variations", [])

            score = 0
            max_score = 0

            # 💠 Category: فقط برابر دقیق یا none
            if self.query_category:
                max_score += 1
                if category == self.query_category.strip().lower():
                    score += 1
                else:
                    continue  # ❌ اگر دسته‌بندی متفاوت بود، حذفش کن

            # ✅ Brand
            if self.brand:
                max_score += 1
                if self.brand.strip().lower() == brand:
                    score += 1

            # ✅ Feature keywords
            if self.feature_keywords:
                max_score += 1
                if any(k.lower() in features or k.lower() in name for k in self.feature_keywords):
                    score += 1

            # ✅ Sizes
            if self.size_preferences and sizes:
                max_score += 1
                if any(s.upper() in sizes for s in self.size_preferences):
                    score += 1

            # ✅ Price
            in_price = True
            if self.price_min is not None and price < self.price_min:
                in_price = False
            if self.price_max is not None and price > self.price_max:
                in_price = False

            near_price = False
            if not in_price:
                if self.price_min and price >= self.price_min - self.price_tolerance:
                    near_price = True
                if self.price_max and price <= self.price_max + self.price_tolerance:
                    near_price = True

            if self.price_min or self.price_max:
                max_score += 1
                if in_price:
                    score += 1
                elif near_price:
                    score += 0.5  # 👈 امتیاز کمتر

            # امتیاز کافی برای ورود به لیست
            if max_score == 0:
                continue

            match_ratio = score / max_score
            if match_ratio >= 0.8:
                exact_matches.append((score, chunk))
            elif match_ratio >= 0.5:
                near_matches.append((score, chunk))

        if not exact_matches and not near_matches:
            return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

        # 📊 رتبه‌بندی با ترکیب امتیاز + شباهت برداری
        def rank(chunks):
            ranked = []
            for score, chunk in chunks:
                try:
                    sim = np.dot(query_vector, chunk["vector"]) / (norm(query_vector) * norm(chunk["vector"]))
                except:
                    sim = 0
                final_score = score + sim  # هم فیلتر، هم شباهت
                ranked.append((final_score, chunk))
            return [c for _, c in sorted(ranked, reverse=True)[:10]]

        output = []

        def render_block(i, meta):
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

            return (
                f"{i}. **{name}**\n"
                f"💰 قیمت: {price}\n"
                f"{stock_note}\n"
                f"📏 سایزها: {', '.join(sizes)}\n"
                f"🔍 ویژگی‌ها: {features}\n"
                f"🖼️ تصویر: {image}\n"
                f"🔗 [مشاهده محصول]({link})\n"
            )

        exact_top = rank(exact_matches)
        near_top = rank(near_matches)

        if exact_top:
            output.append("🎯 **محصولات دقیقاً مطابق درخواست شما:**\n")
            for i, chunk in enumerate(exact_top, 1):
                output.append(render_block(i, chunk.get("metadata", {})))

        if near_top:
            output.append("\n🔁 **محصولات مشابه که ممکنه برات جالب باشه:**\n")
            for i, chunk in enumerate(near_top, len(exact_top) + 1):
                output.append(render_block(i, chunk.get("metadata", {})))

        return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"
