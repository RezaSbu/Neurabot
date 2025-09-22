from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.db import search_vector_db, get_all_vectors
from app.model_manager import model_manager
from app.query_processor import query_processor
from app.cache_manager import cache_manager
from app.ab_testing import ab_testing
import numpy as np
from numpy.linalg import norm
import re

class QueryKnowledgeBaseTool(BaseModel):
    query_input: str = Field(..., description="User query")
    query_category: Optional[str] = Field(None)
    price_min: Optional[float] = Field(None)
    price_max: Optional[float] = Field(None)
    price_tolerance: Optional[float] = Field(500_000)
    brand: Optional[str] = Field(None)
    feature_keywords: Optional[List[str]] = Field(None)
    size_preferences: Optional[List[str]] = Field(None)
    user_id: Optional[str] = Field(None)  # برای A/B Testing

    async def __call__(self, rdb) -> str:
        # تعیین روش بازیابی بر اساس A/B Testing
        retrieval_variant = ab_testing.get_variant("retrieval_method", self.user_id)
        retrieval_config = ab_testing.get_config("retrieval_method", retrieval_variant)
        
        # پردازش کوئری با استفاده از QueryProcessor
        processed_query = await query_processor.process_query(self.query_input)
        
        # استفاده از تمام زیرسوالات برای جستجو
        all_results = []
        citations = []  # برای ردیابی منابع
        
        for sub_query in processed_query["sub_queries"]:
            # بررسی کش
            cache_key = cache_manager.generate_key("search", sub_query, self.dict())
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                all_results.extend(cached_result)
                continue
            
            # ایجاد امبدینگ برای زیرسوال
            query_vector = await model_manager.get_embedding(sub_query)
            
            # جستجو در دیتابیس برداری
            if retrieval_config == "hybrid_search":
                top_chunks = await self.hybrid_search(rdb, query_vector, sub_query)
            else:
                top_chunks = await search_vector_db(rdb, query_vector, top_k=200)
            
            # فیلتر کردن و رتبه‌بندی نتایج
            exact_matches, near_matches = await self.filter_chunks(top_chunks)
            
            # ترکیب نتایج
            results = exact_matches + near_matches
            
            # ذخیره در کش
            await cache_manager.set(cache_key, results)
            
            all_results.extend(results)
            
            # اضافه کردن استنادها
            for chunk in results:
                if isinstance(chunk, tuple):
                    chunk = chunk[1]
                citations.append({
                    "chunk_id": chunk.get("chunk_id"),
                    "title": chunk.get("metadata", {}).get("name", "بدون عنوان"),
                    "url": chunk.get("metadata", {}).get("link", "#")
                })
        
        # حذف نتایج تکراری
        unique_results = []
        seen = set()
        for result in all_results:
            if isinstance(result, tuple):
                chunk = result[1]
            else:
                chunk = result
            chunk_id = chunk.get("chunk_id")
            if chunk_id not in seen:
                seen.add(chunk_id)
                unique_results.append(result)
        
        # فرمت‌دهی نتایج
        output = self.format_results(unique_results)
        
        # اضافه کردن استنادها به انتهای پاسخ
        if citations:
            output = await response_reflector.extract_citations(output, citations)
        
        return output

    async def hybrid_search(self, rdb, query_vector, query_text, top_k=200):
        """جستجو ترکیبی (برداری + کلیدواژه)"""
        # جستجو برداری
        vector_results = await search_vector_db(rdb, query_vector, top_k=top_k)
        
        # جستجو مبتنی بر کلیدواژه (BM25)
        keyword_results = await self.keyword_search(rdb, query_text, top_k=top_k)
        
        # ترکیب نتایج با روش Reciprocal Rank Fusion
        combined_results = self.reciprocal_rank_fusion(vector_results, keyword_results)
        
        return combined_results

    async def keyword_search(self, rdb, query_text, top_k=200):
        """جستجو مبتنی بر کلیدواژه"""
        # در اینجا می‌توان از قابلیت‌های جستجوی متن کامل Redis استفاده کرد
        # برای سادگی، ما یک جستجوی ساده پیاده‌سازی می‌کنیم
        
        # استخراج کلمات کلیدی از کوئری
        keywords = re.findall(r'\b\w+\b', query_text.lower())
        
        # در عمل، این بخش باید با استفاده از قابلیت‌های جستجوی متن کامل Redis پیاده‌سازی شود
        # برای نمونه، ما فقط نتایج جستجوی برداری را برمی‌گردانیم
        return await search_vector_db(rdb, await model_manager.get_embedding(query_text), top_k=top_k)

    def reciprocal_rank_fusion(self, vector_results, keyword_results, k=60):
        """ترکیب نتایج با روش Reciprocal Rank Fusion"""
        fused_results = {}
        
        # پردازش نتایج برداری
        for rank, chunk in enumerate(vector_results):
            chunk_id = chunk.get("chunk_id")
            if chunk_id not in fused_results:
                fused_results[chunk_id] = {"chunk": chunk, "score": 0}
            fused_results[chunk_id]["score"] += 1 / (k + rank + 1)
        
        # پردازش نتایج کلیدواژه
        for rank, chunk in enumerate(keyword_results):
            chunk_id = chunk.get("chunk_id")
            if chunk_id not in fused_results:
                fused_results[chunk_id] = {"chunk": chunk, "score": 0}
            fused_results[chunk_id]["score"] += 1 / (k + rank + 1)
        
        # مرتب‌سازی نتایج ترکیبی
        sorted_results = sorted(fused_results.values(), key=lambda x: x["score"], reverse=True)
        
        return [item["chunk"] for item in sorted_results]

    def parse_price(self, price: Optional[float]) -> Optional[float]:
        """تبدیل قیمت به تومان"""
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

    async def filter_chunks(self, chunks):
        """فیلتر کردن و رتبه‌بندی نتایج"""
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

            # استخراج دسته‌بندی از کوئری اگر ارائه نشده باشد
            query_category = self.query_category
            if not query_category:
                query_lower = self.query_input.lower()
                # ... کد استخراج دسته‌بندی از کد اصلی ...

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

    def format_results(self, results):
        """فرمت‌دهی نتایج برای نمایش به کاربر"""
        # ... کد فرمت‌دهی از کد اصلی ...
        pass