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
        # Extract category from query_input if not provided
        query_category = self.query_category
        if not query_category:
            query_lower = self.query_input.lower()

            # Synonym mapping for common user terms
            synonym_map = {
                "کفش": "پوشاک موتورسواری",
                "چکمه": "پوشاک موتورسواری",
                "بوت": "پوشاک موتورسواری",
                "لباس": "پوشاک موتورسواری",
                "کاپشن": "پوشاک موتورسواری",
                "دستکش": "پوشاک موتورسواری",
                "پوشاک": "پوشاک موتورسواری",
                "کلاه": "کلاه کاسکت",
                "کاسکت": "کلاه کاسکت",
                "کلاه ایمنی": "کلاه کاسکت",
                "لاستیک": "لاستیک موتور سیکلت",
                "تایر": "لاستیک موتور سیکلت",
                "چرخ": "لاستیک موتور سیکلت",
                "پروتکشن": "پروتکشن موتور سیکلت",
                "محافظ": "پروتکشن موتور سیکلت",
                "زره": "پروتکشن موتور سیکلت",
                "باکس": "باکس موتور سیکلت",
                "جعبه": "باکس موتور سیکلت",
                "صندوق": "باکس موتور سیکلت",
                "گردگیر": "لوازم جانبی موتورسیکلت",
                "لوازم جانبی": "لوازم جانبی موتورسیکلت",
                "لوازم": "لوازم جانبی موتورسیکلت",
            }
            # First check synonyms
            for keyword, category in synonym_map.items():
                if keyword in query_lower:
                    query_category = category
                    break

            # Fallback to original keyword-based detection
            if not query_category:
                if "روغن ترمز" in query_lower:
                    query_category = "روغن ترمز"
                elif "روغن موتور" in query_lower:
                    query_category = "روغن موتور"
                elif "دستکش" in query_lower or "کاپشن" in query_lower:
                    query_category = "پوشاک موتورسواری"
                elif "کلاه کاسکت" in query_lower or "کاسکت" in query_lower:
                    query_category = "کلاه کاسکت"
                elif "لاستیک" in query_lower:
                    query_category = "لاستیک موتور سیکلت"
                elif "پروتکشن" in query_lower:
                    query_category = "پروتکشن موتور سیکلت"
                elif "باکس" in query_lower:
                    query_category = "باکس موتور سیکلت"
                elif "لوازم جانبی" in query_lower or "گردگیر" in query_lower:
                    query_category = "لوازم جانبی موتورسیکلت"
                elif "آیروکس" in query_lower:
                    query_category = "لوازم آیروکس و طرح آیروکس (NVX)"
                elif "کلیک" in query_lower:
                    query_category = "لوازم کلیک و طرح کلیک"
                elif "شاخ کلاه" in query_lower:
                    query_category = "لوازم کلاه کاسکت"
                else:
                    query_category = query_lower.split()[0]

        def parse_price(price: Optional[float]) -> Optional[float]:
            if price is None:
                return None
            if price > 10_000:
                return price
            if price <= 10:
                return price * 1_000_000
            elif price <= 100:
                return price * 1_000_000
            else:
                return price * 1_000

        # Parse price_min and price_max
        self.price_min = parse_price(self.price_min)
        self.price_max = parse_price(self.price_max)

        query_vector = await get_embedding(self.query_input)

        async def filter_chunks(chunks):
            exact_matches = []
            price_close = []
            size_close = []
            feature_close = []

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

                # Strict category matching
                if query_category.lower() not in category and query_category.lower() not in name:
                    continue

                has_exact_size = True
                if self.size_preferences:
                    has_exact_size = any(s.upper() in sizes for s in self.size_preferences)

                score = 0
                max_score = 0

                if query_category:
                    max_score += 4
                    if query_category.lower() in category or query_category.lower() in name:
                        score += 4
                    elif any(word in category or word in name for word in query_category.lower().split()):
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
                elif query_category in ["روغن ترمز", "روغن موتور"]:
                    max_score += 1
                    if any(dot in features for dot in ["dot3", "dot4", "dot5", "10w40", "5w30", "10w60"]):
                        score += 1
                elif "لاستیک" in query_category:
                    max_score += 1
                    if "پهنا" in features:
                        score += 1
                elif "پوشاک" in query_category or "کلاه" in query_category:
                    max_score += 1
                    if "سبک" in features:
                        score += 1
                elif "لوازم" in query_category:
                    max_score += 1
                    if "وزن" in features or "جنس" in features:
                        score += 1

                if self.size_preferences:
                    max_score += 2
                    if has_exact_size:
                        score += 2

                out_of_range = False
                if self.price_min and price < self.price_min - 2 * self.price_tolerance:
                    out_of_range = True
                if self.price_max and price > self.price_max + 2 * self.price_tolerance:
                    out_of_range = True

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
                        score += 1.5
                    elif diff <= 2 * self.price_tolerance:
                        score += 0.5

                if max_score == 0 or out_of_range:
                    continue
                elif score >= max_score * 0.8 and has_exact_size and in_range:
                    exact_matches.append((score, chunk))
                elif diff <= 4 * self.price_tolerance:
                    if diff <= self.price_tolerance or (diff <= 2 * self.price_tolerance and has_exact_size):
                        price_close.append((score, chunk, price_status, diff, has_exact_size))
                    elif has_exact_size:
                        size_close.append((score, chunk, price_status, diff, has_exact_size))
                    elif not self.size_preferences:
                        feature_close.append((score, chunk, price_status, diff, has_exact_size))

            # Allocate near matches
            max_total = 10
            num_exact = len(exact_matches)
            near_matches = []
            if num_exact < max_total:
                remaining = min(max_total - num_exact, 5)
                price_alloc = max(1, int(remaining * 0.7))
                size_feature_alloc = remaining - price_alloc
                if self.size_preferences:
                    near_matches = price_close[:price_alloc] + size_close[:size_feature_alloc]
                else:
                    near_matches = price_close[:price_alloc] + feature_close[:size_feature_alloc]
                if len(near_matches) < 5 and feature_close:
                    near_matches.extend(feature_close[:(5 - len(near_matches))])
            elif num_exact == max_total:
                near_matches = []

            return exact_matches, near_matches

        top_chunks = await search_vector_db(rdb, query_vector, top_k=200)
        exact_matches, near_matches = await filter_chunks(top_chunks)

        if not exact_matches and not near_matches:
            all_chunks = await get_all_vectors(rdb)
            exact_matches, near_matches = await filter_chunks(all_chunks)

        if not exact_matches and not near_matches:
            return f"❌ محصولی برای '{query_category}' در پایگاه داده پیدا نشد. لطفاً دسته‌بندی یا ویژگی‌های دیگری (مثل برند یا استاندارد خاص) را امتحان کنید یا با پشتیبانی تماس بگیرید."

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
                    final_score += 1
                elif diff <= 2 * self.price_tolerance:
                    final_score += 0.5
                if has_size and self.size_preferences:
                    final_score += 0.5
                ranked.append((final_score, chunk, status, diff, has_size))
            return sorted(ranked, reverse=True)[:10]

        def format_note(status, diff, has_size):
            notes = []
            if self.size_preferences and not has_size:
                notes.append(f"⚠️ سایز دقیق درخواستی (مثلاً {', '.join(self.size_preferences)}) موجود نیست")
            if diff > 0 and diff <= self.price_tolerance:
                notes.append(f"💡 قیمت این محصول نزدیک به بودجه شماست (اختلاف: {int(diff):,} تومان)")
            elif diff > self.price_tolerance and diff <= 2 * self.price_tolerance and has_size:
                notes.append(f"💡 این محصول سایز دقیق شما را دارد، اما قیمت کمی متفاوت است (اختلاف: {int(diff):,} تومان)")
            elif diff > 2 * self.price_tolerance and has_size:
                notes.append(f"💡 این محصول سایز دقیق شما را دارد، اما قیمت متفاوت است (اختلاف: {int(diff):,} تومان)")
            elif diff > 0 and status == "cheaper":
                notes.append("💡 گزینه‌ای اقتصادی‌تر نسبت به درخواست شما (قیمت کمتر)")
            elif diff > 0 and status == "expensive":
                notes.append("💡 این مورد گران‌تر از محدوده تعیین‌شده است (قیمت بیشتر)")
            return " | ".join(notes) if notes else "💡 مورد نزدیک با ویژگی‌های مشابه"

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
                f"{i}. **{name}**\n"
                f"💰 قیمت: {price}\n"
                f"{stock_note}\n"
                f"📏 سایزها: {', '.join(sizes) if sizes else 'نامشخص'}\n"
                f"🔍 ویژگی‌ها: {features if features else 'نامشخص'}\n"
                f"🖼️ تصویر: {image}\n"
                f"🔗 [مشاهده محصول]({link})"
            )
            return f"{line}\n📌 {note}" if note else line

        exact_ranked = rank(exact_matches)
        near_ranked = rank(near_matches, with_status=True)

        output = []

        if exact_ranked:
            output.append("✅ **نتایج دقیق مطابق درخواست شما:**\n")
            for i, (final_score, chunk, _, _, _) in enumerate(exact_ranked, 1):
                note = format_note(None, 0, True)
                output.append(format_chunk(i, chunk, note))

        if near_ranked:
            output.append("\n🔄 **موارد نزدیک با تفاوت جزئی (اولویت با قیمت، سپس سایز یا ویژگی‌ها):**\n")
            for i, (final_score, chunk, status, diff, has_size) in enumerate(near_ranked, len(exact_ranked) + 1):
                note = format_note(status, diff, has_size)
                output.append(format_chunk(i, chunk, note))

        return "\n\n---\n\n".join(output) + "\n\n---\nاین موارد چطور بودن؟ مورد دیگه‌ای نیاز داری؟ 😊"
