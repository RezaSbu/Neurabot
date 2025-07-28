# from pydantic import BaseModel, Field
# from typing import Optional, List
# from app.db import search_vector_db, get_all_vectors
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

#         async def filter_chunks(chunks):
#             exact_matches = []
#             near_matches = []

#             for chunk in chunks:
#                 meta = chunk.get("metadata", {})
#                 price = meta.get("price_numeric", None)
#                 if not isinstance(price, (int, float)):
#                     continue

#                 brand = meta.get("brand", "").lower()
#                 category = meta.get("category", "").lower()
#                 name = meta.get("name", "").lower()
#                 features = meta.get("features_flat", "").lower()
#                 sizes = meta.get("sizes_flat", [])
#                 variations = meta.get("variations", [])

#                 has_exact_size = True
#                 if self.size_preferences:
#                     has_exact_size = any(s.upper() in sizes for s in self.size_preferences)

#                 score = 0
#                 max_score = 0

#                 if self.query_category:
#                     max_score += 5
#                     if self.query_category.lower() in category or self.query_category.lower() in name:
#                         score += 5
#                     elif any(word in category or word in name for word in self.query_category.lower().split()):
#                         score += 1

#                 if self.brand:
#                     max_score += 1
#                     if self.brand.lower() in brand:
#                         score += 1

#                 if self.feature_keywords:
#                     max_score += 1
#                     matched_keywords = sum(1 for k in self.feature_keywords if k.lower() in features or k.lower() in name)
#                     if matched_keywords > 0:
#                         score += min(matched_keywords, 1)

#                 if self.size_preferences:
#                     max_score += 2
#                     if has_exact_size:
#                         score += 2

#                 out_of_range = False
#                 if self.price_min and price < self.price_min - 2 * self.price_tolerance:
#                     out_of_range = True
#                 if self.price_max and price > self.price_max + 2 * self.price_tolerance:
#                     out_of_range = True
#                 if out_of_range:
#                     continue

#                 price_status = "exact"
#                 in_range = True
#                 if self.price_min and price < self.price_min:
#                     in_range = False
#                     price_status = "cheaper"
#                 if self.price_max and price > self.price_max:
#                     in_range = False
#                     price_status = "expensive"

#                 diff = 0
#                 if self.price_min and price < self.price_min:
#                     diff = self.price_min - price
#                 elif self.price_max and price > self.price_max:
#                     diff = price - self.price_max

#                 if self.price_min or self.price_max:
#                     max_score += 2
#                     if in_range:
#                         score += 2
#                     elif diff <= self.price_tolerance:
#                         score += 1.5  # Higher score for price within tolerance
#                     elif diff <= 2 * self.price_tolerance:
#                         score += 0.5

#                 if max_score == 0:
#                     continue
#                 elif score >= max_score * 0.8 and has_exact_size and in_range:
#                     exact_matches.append((score, chunk))
#                 elif diff <= self.price_tolerance or (diff <= 2 * self.price_tolerance and has_exact_size) or score >= max_score * 0.4:
#                     near_matches.append((score, chunk, price_status, diff, has_exact_size))

#             return exact_matches, near_matches

#         top_chunks = await search_vector_db(rdb, query_vector, top_k=200)
#         exact_matches, near_matches = await filter_chunks(top_chunks)

#         if not exact_matches and not near_matches:
#             all_chunks = await get_all_vectors(rdb)
#             exact_matches, near_matches = await filter_chunks(all_chunks)

#         if not exact_matches and not near_matches:
#             return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

#         def rank(chunks, with_status=False):
#             ranked = []
#             for item in chunks:
#                 if with_status:
#                     score, chunk, status, diff, has_size = item
#                 else:
#                     score, chunk = item
#                     status, diff, has_size = None, 0, True
#                 try:
#                     sim = np.dot(query_vector, chunk["vector"]) / (norm(query_vector) * norm(chunk["vector"]))
#                 except:
#                     sim = 0
#                 final_score = score + (sim * 1.5)
#                 if diff <= self.price_tolerance:
#                     final_score += 1  # Strong bonus for price within tolerance
#                 elif diff <= 2 * self.price_tolerance:
#                     final_score += 0.5  # Smaller bonus for price within 2x tolerance
#                 ranked.append((final_score, chunk, status, diff, has_size))
#             return sorted(ranked, reverse=True)[:10]

#         def format_note(status, diff, has_size):
#             if diff > 0 and diff <= self.price_tolerance:
#                 return f"💡 قیمت این محصول نزدیک به بودجه شماست (اختلاف: {int(diff):,} تومان)"
#             elif diff > self.price_tolerance and diff <= 2 * self.price_tolerance and has_size:
#                 return "💡 این محصول سایز دقیق شما را دارد، اما قیمت کمی متفاوت است"
#             elif not has_size:
#                 return "⚠️ سایز دقیق درخواستی (مثلاً XL) موجود نیست"
#             if status == "cheaper":
#                 return "💡 گزینه‌ای اقتصادی‌تر نسبت به درخواست شما (قیمت کمتر)"
#             elif status == "expensive":
#                 return "💡 این مورد کمی گران‌تر از محدوده تعیین‌شده است (قیمت بیشتر)"
#             return "💡 مورد نزدیک با ویژگی‌های مشابه"

#         def format_chunk(i, chunk, note=None):
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
#             line = (
#                 f"{i+1}. **{name}**\n"
#                 f"💰 قیمت: {price}\n"
#                 f"{stock_note}\n"
#                 f"📏 سایزها: {', '.join(sizes)}\n"
#                 f"🔍 ویژگی‌ها: {features}\n"
#                 f"🖼️ تصویر: {image}\n"
#                 f"🔗 [مشاهده محصول]({link})"
#             )
#             return f"{line}\n📌 {note}" if note else line

#         exact_ranked = rank(exact_matches)
#         near_ranked = rank(near_matches, with_status=True)

#         output = []

#         if exact_ranked:
#             output.append("✅ **نتایج دقیق مطابق درخواست شما:**\n")
#             output.extend([format_chunk(i, chunk) for i, chunk, _, _, _ in exact_ranked])

#         if near_ranked:
#             output.append("\n🔄 **موارد نزدیک با تفاوت جزئی (اولویت با قیمت، سپس سایز):**\n")
#             for i, chunk, status, diff, has_size in near_ranked:
#                 note = format_note(status, diff, has_size)
#                 output.append(format_chunk(i, chunk, note=note))

#         return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"






from pydantic import BaseModel, Field
from typing import Optional, List
from app.db import search_vector_db, get_all_vectors
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
        def parse_price(price: Optional[float]) -> Optional[float]:
            if price is None:
                return None
            # If price is already in a reasonable range (e.g., > 10,000), assume it's in Tomans
            if price > 10_000:
                return price
            # Handle "toman" shorthand (e.g., 1 تومن = 1,000,000, 1.5 تومن = 1,500,000)
            if price <= 10:  # Assume small numbers (e.g., 1, 1.5) mean millions
                return price * 1_000_000
            elif price <= 100:  # Assume numbers like 25 mean 25 million
                return price * 1_000_000
            else:  # Assume numbers like 500, 900 mean thousands
                return price * 1_000
            return price

        # Parse price_min and price_max
        self.price_min = parse_price(self.price_min)
        self.price_max = parse_price(self.price_max)

        query_vector = await get_embedding(self.query_input)

        async def filter_chunks(chunks):
            exact_matches = []
            near_matches = []

            for chunk in chunks:
                meta = chunk.get("metadata", {})
                price = meta.get("price_numeric", None)
                if not isinstance(price, (int, float)):
                    continue

                brand = meta.get("brand", "").lower()
                category = meta.get("category", "").lower()
                name = meta.get("name", "").lower()
                features = meta.get("features_flat", "").lower()
                sizes = meta.get("sizes_flat", [])
                variations = meta.get("variations", [])

                has_exact_size = True
                if self.size_preferences:
                    has_exact_size = any(s.upper() in sizes for s in self.size_preferences)

                score = 0
                max_score = 0

                if self.query_category:
                    max_score += 5
                    if self.query_category.lower() in category or self.query_category.lower() in name:
                        score += 5
                    elif any(word in category or word in name for word in self.query_category.lower().split()):
                        score += 1

                if self.brand:
                    max_score += 1
                    if self.brand.lower() in brand:
                        score += 1

                if self.feature_keywords:
                    max_score += 1
                    matched_keywords = sum(1 for k in self.feature_keywords if k.lower() in features or k.lower() in name)
                    if matched_keywords > 0:
                        score += min(matched_keywords, 1)

                if self.size_preferences:
                    max_score += 2
                    if has_exact_size:
                        score += 2

                out_of_range = False
                if self.price_min and price < self.price_min - 2 * self.price_tolerance:
                    out_of_range = True
                if self.price_max and price > self.price_max + 2 * self.price_tolerance:
                    out_of_range = True
                if out_of_range:
                    continue

                price_status = "exact"
                in_range = True
                if self.price_min and price < self.price_min:
                    in_range = False
                    price_status = "cheaper"
                if self.price_max and price > self.price_max:
                    in_range = False
                    price_status = "expensive"

                diff = 0
                if self.price_min and price < self.price_min:
                    diff = self.price_min - price
                elif self.price_max and price > self.price_max:
                    diff = price - self.price_max

                if self.price_min or self.price_max:
                    max_score += 2
                    if in_range:
                        score += 2
                    elif diff <= self.price_tolerance:
                        score += 1.5  # Higher score for price within tolerance
                    elif diff <= 2 * self.price_tolerance:
                        score += 0.5

                if max_score == 0:
                    continue
                elif score >= max_score * 0.8 and has_exact_size and in_range:
                    exact_matches.append((score, chunk))
                elif diff <= self.price_tolerance or (diff <= 2 * self.price_tolerance and has_exact_size) or score >= max_score * 0.4:
                    near_matches.append((score, chunk, price_status, diff, has_exact_size))

            return exact_matches, near_matches

        top_chunks = await search_vector_db(rdb, query_vector, top_k=200)
        exact_matches, near_matches = await filter_chunks(top_chunks)

        if not exact_matches and not near_matches:
            all_chunks = await get_all_vectors(rdb)
            exact_matches, near_matches = await filter_chunks(all_chunks)

        if not exact_matches and not near_matches:
            return "❌ محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."

        def rank(chunks, with_status=False):
            ranked = []
            for item in chunks:
                if with_status:
                    score, chunk, status, diff, has_size = item
                else:
                    score, chunk = item
                    status, diff, has_size = None, 0, True
                try:
                    sim = np.dot(query_vector, chunk["vector"]) / (norm(query_vector) * norm(chunk["vector"]))
                except:
                    sim = 0
                final_score = score + (sim * 1.5)
                if diff <= self.price_tolerance:
                    final_score += 1  # Strong bonus for price within tolerance
                elif diff <= 2 * self.price_tolerance:
                    final_score += 0.5  # Smaller bonus for price within 2x tolerance
                ranked.append((final_score, chunk, status, diff, has_size))
            return sorted(ranked, reverse=True)[:10]

        def format_note(status, diff, has_size):
            if diff > 0 and diff <= self.price_tolerance:
                return f"💡 قیمت این محصول نزدیک به بودجه شماست (اختلاف: {int(diff):,} تومان)"
            elif diff > self.price_tolerance and diff <= 2 * self.price_tolerance and has_size:
                return "💡 این محصول سایز دقیق شما را دارد، اما قیمت کمی متفاوت است"
            elif not has_size:
                return "⚠️ سایز دقیق درخواستی (مثلاً XL) موجود نیست"
            if status == "cheaper":
                return "💡 گزینه‌ای اقتصادی‌تر نسبت به درخواست شما (قیمت کمتر)"
            elif status == "expensive":
                return "💡 این مورد کمی گران‌تر از محدوده تعیین‌شده است (قیمت بیشتر)"
            return "💡 مورد نزدیک با ویژگی‌های مشابه"

        def format_chunk(i, chunk, note=None):
            meta = chunk.get("metadata", {})
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
            line = (
                f"{i+1}. **{name}**\n"
                f"💰 قیمت: {price}\n"
                f"{stock_note}\n"
                f"📏 سایزها: {', '.join(sizes)}\n"
                f"🔍 ویژگی‌ها: {features}\n"
                f"🖼️ تصویر: {image}\n"
                f"🔗 [مشاهده محصول]({link})"
            )
            return f"{line}\n📌 {note}" if note else line

        exact_ranked = rank(exact_matches)
        near_ranked = rank(near_matches, with_status=True)

        output = []

        if exact_ranked:
            output.append("✅ **نتایج دقیق مطابق درخواست شما:**\n")
            output.extend([format_chunk(i, chunk) for i, chunk, _, _, _ in exact_ranked])

        if near_ranked:
            output.append("\n🔄 **موارد نزدیک با تفاوت جزئی (اولویت با قیمت، سپس سایز):**\n")
            for i, chunk, status, diff, has_size in near_ranked:
                note = format_note(status, diff, has_size)
                output.append(format_chunk(i, chunk, note=note))

        return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"