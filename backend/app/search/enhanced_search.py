from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from numpy.linalg import norm
import asyncio
import json
from datetime import datetime

from app.db import search_hybrid_db, search_vector_db, search_keyword_db
from app.openai import get_embedding
from app.config import settings
from app.memory.customer_profile import CustomerProfile

class EnhancedSearchEngine:
    """موتور جستجوی پیشرفته با قابلیت reranking و شخصی‌سازی"""
    
    def __init__(self):
        self.search_history = {}
        self.performance_metrics = {
            "total_searches": 0,
            "successful_matches": 0,
            "average_response_time": 0.0
        }

    async def semantic_search_with_reranking(
        self, 
        query: str, 
        user_profile: Optional[CustomerProfile] = None,
        category: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """جستجوی چندمرحله‌ای با reranking هوشمند"""
        
        start_time = datetime.now()
        
        # Stage 1: Broad semantic search with higher top_k
        candidates = await self._broad_search(query, category, filters)
        
        if not candidates:
            return []
        
        # Stage 2: Rerank based on user profile and context
        if user_profile:
            personalized_results = await self._personalize_results(candidates, user_profile)
        else:
            personalized_results = candidates
        
        # Stage 3: Apply business logic and final ranking
        final_results = await self._apply_business_rules(personalized_results, query, filters)
        
        # Stage 4: Diversity optimization
        diverse_results = self._optimize_diversity(final_results)
        
        # Update performance metrics
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        self._update_metrics(len(diverse_results) > 0, response_time)
        
        return diverse_results[:settings.RERANK_TOP_K]

    async def _broad_search(
        self, 
        query: str, 
        category: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """مرحله اول: جستجوی گسترده"""
        
        # تولید embedding برای query
        query_vector = await get_embedding(query)
        
        # جستجوی ترکیبی (vector + keyword)
        results = await search_hybrid_db(
            rdb=None,  # باید از dependency injection استفاده شود
            query_vector=query_vector,
            query_text=query,
            top_k=settings.VECTOR_SEARCH_TOP_K,
            category=category,
            budget_range=filters.get('budget_range') if filters else None,
            alpha=settings.HYBRID_SEARCH_ALPHA
        )
        
        return results

    async def _personalize_results(
        self, 
        candidates: List[Dict[str, Any]], 
        user_profile: CustomerProfile
    ) -> List[Dict[str, Any]]:
        """مرحله دوم: شخصی‌سازی نتایج بر اساس پروفایل کاربر"""
        
        personalized_candidates = []
        
        for candidate in candidates:
            metadata = candidate.get('metadata', {})
            
            # محاسبه امتیاز شخصی‌سازی
            personalization_score = self._calculate_personalization_score(metadata, user_profile)
            
            # ترکیب امتیاز اصلی با امتیاز شخصی‌سازی
            original_score = candidate.get('score', 0.0)
            combined_score = (original_score * 0.7) + (personalization_score * 0.3)
            
            candidate['personalization_score'] = personalization_score
            candidate['combined_score'] = combined_score
            candidate['personalization_factors'] = self._get_personalization_factors(metadata, user_profile)
            
            personalized_candidates.append(candidate)
        
        # مرتب‌سازی بر اساس امتیاز ترکیبی
        return sorted(personalized_candidates, key=lambda x: x['combined_score'], reverse=True)

    def _calculate_personalization_score(
        self, 
        metadata: Dict[str, Any], 
        user_profile: CustomerProfile
    ) -> float:
        """محاسبه امتیاز شخصی‌سازی"""
        
        score = 0.0
        
        # امتیاز برند ترجیحی
        brand = metadata.get('brand', '').lower()
        if brand in [b.lower() for b in user_profile.preferred_brands]:
            score += 0.3
        elif brand in [b.lower() for b in user_profile.avoided_brands]:
            score -= 0.2
        
        # امتیاز دسته‌بندی محبوب
        category = metadata.get('category', '')
        if user_profile.purchase_patterns.get('favorite_categories'):
            favorite_cats = [cat[0] for cat in user_profile.purchase_patterns['favorite_categories']]
            if category in favorite_cats:
                score += 0.2
        
        # امتیاز محدوده قیمت
        price_numeric = metadata.get('price_numeric', 0)
        if user_profile.budget_range:
            if self._price_fits_budget(price_numeric, user_profile.budget_range):
                score += 0.2
            else:
                # جریمه برای محصولات خارج از بودجه
                score -= 0.1
        
        # امتیاز حساسیت قیمت
        if user_profile.price_sensitivity == "high" and price_numeric < 5000000:
            score += 0.1
        elif user_profile.price_sensitivity == "low" and price_numeric > 10000000:
            score += 0.1
        
        # امتیاز سازگاری با موتور
        if user_profile.motorcycle_model:
            compatibility_score = self._assess_motorcycle_compatibility(
                metadata, user_profile.motorcycle_model
            )
            score += compatibility_score * 0.2
        
        # امتیاز سطح تخصص
        if user_profile.technical_expertise == "expert":
            # کاربران متخصص ممکن است محصولات پیچیده‌تر را ترجیح دهند
            if 'حرفه‌ای' in metadata.get('features_flat', '') or price_numeric > 8000000:
                score += 0.1
        elif user_profile.technical_expertise == "beginner":
            # کاربران مبتدی محصولات ساده‌تر را ترجیح می‌دهند
            if 'آسان' in metadata.get('features_flat', '') or price_numeric < 6000000:
                score += 0.1
        
        return max(0.0, min(1.0, score))  # نرمالیزه کردن بین 0 و 1

    def _price_fits_budget(self, price: float, budget_range: str) -> bool:
        """بررسی تناسب قیمت با بودجه"""
        budget_limits = {
            "زیر ۵ میلیون": (0, 5000000),
            "۵-۱۰ میلیون": (5000000, 10000000),
            "۱۰-۲۰ میلیون": (10000000, 20000000),
            "بیش از ۲۰ میلیون": (20000000, float('inf'))
        }
        
        if budget_range in budget_limits:
            min_price, max_price = budget_limits[budget_range]
            return min_price <= price <= max_price
        
        return True

    def _assess_motorcycle_compatibility(self, metadata: Dict, motorcycle_model: str) -> float:
        """ارزیابی سازگاری با مدل موتور"""
        category = metadata.get('category', '').lower()
        name = metadata.get('name', '').lower()
        motorcycle_lower = motorcycle_model.lower()
        
        # سازگاری کامل
        if motorcycle_lower in name:
            return 1.0
        
        # سازگاری بر اساس دسته‌بندی
        if 'لاستیک' in category:
            # قوانین سازگاری لاستیک
            compatibility_map = {
                'کلیک': 0.9 if any(size in name for size in ['110', '120', '130']) else 0.3,
                'آیروکس': 0.9 if any(size in name for size in ['110', '120', '130']) else 0.3,
                'هیوسانگ': 0.9 if any(size in name for size in ['110', '120']) else 0.3,
                'آپاچی': 0.9 if any(size in name for size in ['120', '140']) else 0.3,
                'بنلی': 0.9 if any(size in name for size in ['120', '140']) else 0.3
            }
            
            for bike_type, score in compatibility_map.items():
                if bike_type in motorcycle_lower:
                    return score
        
        elif 'پروتکشن' in category:
            # پروتکشن‌های مخصوص
            if motorcycle_lower in name:
                return 1.0
            else:
                return 0.5  # پروتکشن عمومی
        
        # سازگاری عمومی برای سایر دسته‌ها
        return 0.7

    def _get_personalization_factors(
        self, 
        metadata: Dict[str, Any], 
        user_profile: CustomerProfile
    ) -> List[str]:
        """استخراج عوامل شخصی‌سازی"""
        factors = []
        
        brand = metadata.get('brand', '')
        if brand in user_profile.preferred_brands:
            factors.append(f"برند ترجیحی: {brand}")
        
        category = metadata.get('category', '')
        if user_profile.purchase_patterns.get('favorite_categories'):
            favorite_cats = [cat[0] for cat in user_profile.purchase_patterns['favorite_categories']]
            if category in favorite_cats:
                factors.append(f"دسته محبوب: {category}")
        
        price_numeric = metadata.get('price_numeric', 0)
        if user_profile.budget_range and self._price_fits_budget(price_numeric, user_profile.budget_range):
            factors.append(f"مناسب بودجه: {user_profile.budget_range}")
        
        if user_profile.motorcycle_model:
            compatibility = self._assess_motorcycle_compatibility(metadata, user_profile.motorcycle_model)
            if compatibility > 0.7:
                factors.append(f"سازگار با: {user_profile.motorcycle_model}")
        
        return factors

    async def _apply_business_rules(
        self, 
        candidates: List[Dict[str, Any]], 
        query: str,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """مرحله سوم: اعمال قوانین تجاری"""
        
        enhanced_candidates = []
        
        for candidate in candidates:
            metadata = candidate.get('metadata', {})
            
            # محاسبه امتیاز تجاری
            business_score = self._calculate_business_score(metadata, query)
            
            # ترکیب امتیاز فعلی با امتیاز تجاری
            current_score = candidate.get('combined_score', candidate.get('score', 0.0))
            final_score = (current_score * 0.8) + (business_score * 0.2)
            
            candidate['business_score'] = business_score
            candidate['final_score'] = final_score
            candidate['business_factors'] = self._get_business_factors(metadata)
            
            enhanced_candidates.append(candidate)
        
        # مرتب‌سازی نهایی
        return sorted(enhanced_candidates, key=lambda x: x['final_score'], reverse=True)

    def _calculate_business_score(self, metadata: Dict[str, Any], query: str) -> float:
        """محاسبه امتیاز تجاری"""
        score = 0.0
        
        # امتیاز موجودی
        stock = metadata.get('stock', '')
        if 'موجود' in stock:
            if any(char.isdigit() and int(char) <= 2 for char in stock):
                score += 0.1  # موجودی کم - فوریت خرید
            else:
                score += 0.3  # موجودی مناسب
        else:
            score -= 0.2  # ناموجود
        
        # امتیاز برند
        brand = metadata.get('brand', '').lower()
        brand_scores = {
            'yamaha': 0.3, 'honda': 0.3, 'suzuki': 0.25, 'kawasaki': 0.25,
            'mt': 0.2, 'smk': 0.2, 'soman': 0.2, 'scoyco': 0.15,
            'fulmer': 0.1, 'beon': 0.1, 'qike': 0.1, 'redline': 0.05,
            'نامشخص': -0.1
        }
        score += brand_scores.get(brand, 0.0)
        
        # امتیاز قیمت (sweet spot برای فروش)
        price_numeric = metadata.get('price_numeric', 0)
        if 3000000 <= price_numeric <= 12000000:  # رنج قیمت مطلوب
            score += 0.2
        elif price_numeric < 1000000:  # خیلی ارزان - ممکن است کیفیت پایین باشد
            score -= 0.1
        
        # امتیاز تطابق با query
        name = metadata.get('name', '').lower()
        features = metadata.get('features_flat', '').lower()
        query_lower = query.lower()
        
        # تطابق دقیق با نام
        if query_lower in name:
            score += 0.3
        
        # تطابق با ویژگی‌ها
        query_words = query_lower.split()
        feature_matches = sum(1 for word in query_words if word in features)
        if feature_matches > 0:
            score += min(0.2, feature_matches * 0.05)
        
        return max(0.0, min(1.0, score))

    def _get_business_factors(self, metadata: Dict[str, Any]) -> List[str]:
        """استخراج عوامل تجاری"""
        factors = []
        
        stock = metadata.get('stock', '')
        if 'موجود' in stock:
            if any(char.isdigit() and int(char) <= 2 for char in stock):
                factors.append("⚠️ موجودی محدود")
            else:
                factors.append("✅ موجود در انبار")
        else:
            factors.append("❌ ناموجود")
        
        brand = metadata.get('brand', '')
        if brand.lower() in ['yamaha', 'honda', 'suzuki', 'kawasaki', 'mt', 'smk']:
            factors.append(f"🏆 برند معتبر: {brand}")
        
        price_numeric = metadata.get('price_numeric', 0)
        if 3000000 <= price_numeric <= 12000000:
            factors.append("💰 قیمت مناسب")
        elif price_numeric < 3000000:
            factors.append("💵 اقتصادی")
        elif price_numeric > 12000000:
            factors.append("💎 پریمیوم")
        
        return factors

    def _optimize_diversity(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """بهینه‌سازی تنوع نتایج"""
        if len(results) <= 5:
            return results
        
        diverse_results = []
        seen_brands = set()
        seen_categories = set()
        seen_price_ranges = set()
        
        # مرحله اول: انتخاب بهترین‌ها با تنوع برند
        for result in results:
            metadata = result.get('metadata', {})
            brand = metadata.get('brand', 'نامشخص')
            category = metadata.get('category', 'نامشخص')
            price_numeric = metadata.get('price_numeric', 0)
            
            # تعیین رنج قیمت
            if price_numeric < 5000000:
                price_range = "budget"
            elif price_numeric < 10000000:
                price_range = "mid"
            else:
                price_range = "premium"
            
            # اولویت به تنوع برند
            if len(diverse_results) < 3:
                diverse_results.append(result)
                seen_brands.add(brand)
                seen_categories.add(category)
                seen_price_ranges.add(price_range)
            else:
                # بررسی تنوع
                diversity_score = 0
                if brand not in seen_brands:
                    diversity_score += 1
                if category not in seen_categories:
                    diversity_score += 1
                if price_range not in seen_price_ranges:
                    diversity_score += 1
                
                # اگر تنوع خوبی دارد یا امتیاز بالایی دارد، اضافه کن
                if diversity_score > 0 or result.get('final_score', 0) > 0.8:
                    diverse_results.append(result)
                    seen_brands.add(brand)
                    seen_categories.add(category)
                    seen_price_ranges.add(price_range)
                
                if len(diverse_results) >= settings.RERANK_TOP_K:
                    break
        
        # اگر نتایج کافی نداریم، بقیه را اضافه کن
        if len(diverse_results) < settings.RERANK_TOP_K:
            remaining = [r for r in results if r not in diverse_results]
            diverse_results.extend(remaining[:settings.RERANK_TOP_K - len(diverse_results)])
        
        return diverse_results

    async def multi_vector_search(self, query: str, rdb) -> List[Dict[str, Any]]:
        """جستجو با استفاده از چندین embedding model (برای آینده)"""
        # فعلاً از یک embedding استفاده می‌کنیم، اما می‌توان گسترش داد
        query_vector = await get_embedding(query)
        
        # می‌توان embedding‌های مختلف تولید کرد و نتایج را ترکیب کرد
        # مثلاً embedding مخصوص domain یا embedding‌های مختلف OpenAI
        
        return await search_vector_db(rdb, query_vector, top_k=settings.VECTOR_SEARCH_TOP_K)

    def _update_metrics(self, successful: bool, response_time: float) -> None:
        """به‌روزرسانی متریک‌های عملکرد"""
        self.performance_metrics["total_searches"] += 1
        
        if successful:
            self.performance_metrics["successful_matches"] += 1
        
        # محاسبه میانگین زمان پاسخ
        current_avg = self.performance_metrics["average_response_time"]
        total_searches = self.performance_metrics["total_searches"]
        
        new_avg = ((current_avg * (total_searches - 1)) + response_time) / total_searches
        self.performance_metrics["average_response_time"] = new_avg

    def get_performance_metrics(self) -> Dict[str, Any]:
        """دریافت متریک‌های عملکرد"""
        success_rate = 0.0
        if self.performance_metrics["total_searches"] > 0:
            success_rate = (
                self.performance_metrics["successful_matches"] / 
                self.performance_metrics["total_searches"]
            ) * 100
        
        return {
            **self.performance_metrics,
            "success_rate_percentage": round(success_rate, 2)
        }

    async def get_search_suggestions(self, partial_query: str, rdb) -> List[str]:
        """پیشنهاد جستجو بر اساس query ناقص"""
        suggestions = []
        
        # پیشنهادات پایه بر اساس دسته‌بندی‌ها
        base_suggestions = [
            "کلاه کاسکت", "دستکش", "لاستیک", "کاپشن", "پروتکشن",
            "باکس", "لوازم جانبی", "آیروکس", "کلیک"
        ]
        
        # فیلتر بر اساس query جزئی
        for suggestion in base_suggestions:
            if partial_query.lower() in suggestion.lower():
                suggestions.append(suggestion)
        
        # اگر پیشنهاد کافی نداریم، پیشنهادات مرتبط اضافه کن
        if len(suggestions) < 3:
            related_suggestions = [
                f"{partial_query} اسپرت",
                f"{partial_query} شهری", 
                f"{partial_query} ارزان"
            ]
            suggestions.extend(related_suggestions[:3 - len(suggestions)])
        
        return suggestions[:5]  # حداکثر 5 پیشنهاد

