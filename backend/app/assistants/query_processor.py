"""
سیستم پردازش پیشرفته سوالات پیچیده و چندمرحله‌ای
"""
import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class QueryComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    MULTI_STEP = "multi_step"

class QueryIntent(Enum):
    SEARCH_PRODUCT = "search_product"
    COMPARE_PRODUCTS = "compare_products"
    GET_RECOMMENDATIONS = "get_recommendations"
    GET_INFO = "get_info"
    FILTER_PRODUCTS = "filter_products"
    BUDGET_PLANNING = "budget_planning"

@dataclass
class ExtractedEntity:
    type: str
    value: str
    confidence: float
    context: Optional[str] = None

@dataclass
class QueryContext:
    season: Optional[str] = None
    usage_type: Optional[str] = None  # شهری، کراسی، مسافرتی
    experience_level: Optional[str] = None  # مبتدی، متوسط، حرفه‌ای
    urgency: Optional[str] = None  # فوری، عادی
    previous_mentions: List[str] = None

class AdvancedQueryProcessor:
    def __init__(self):
        self.season_keywords = {
            "تابستان": ["تابستان", "گرم", "داغ", "آفتاب", "summer"],
            "زمستان": ["زمستان", "سرد", "برف", "باران", "winter"],
            "چهارفصل": ["چهارفصل", "تمام فصول", "همه فصل", "all season"]
        }
        
        self.usage_keywords = {
            "شهری": ["شهری", "شهر", "ترافیک", "daily", "commute"],
            "کراسی": ["کراسی", "offroad", "کوه", "مغاک", "adventure"],
            "مسافرتی": ["مسافرتی", "سفر", "جاده", "long distance", "touring"]
        }
        
        self.experience_keywords = {
            "مبتدی": ["مبتدی", "تازه کار", "beginner", "novice"],
            "متوسط": ["متوسط", "intermediate"],
            "حرفه‌ای": ["حرفه‌ای", "pro", "expert", "advanced"]
        }

    async def process_query(self, query: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        پردازش کامل سوال کاربر
        """
        # تشخیص پیچیدگی سوال
        complexity = self._analyze_complexity(query)
        
        # استخراج intent
        intent = self._extract_intent(query, chat_history)
        
        # استخراج entities
        entities = self._extract_entities(query)
        
        # استخراج context
        context = self._extract_context(query, chat_history)
        
        # تشخیص سوالات چندمرحله‌ای
        multi_step_queries = self._detect_multi_step(query, chat_history)
        
        # پردازش و بهبود query
        refined_query = self._refine_query(query, entities, context)
        
        return {
            "original_query": query,
            "complexity": complexity,
            "intent": intent,
            "entities": entities,
            "context": context,
            "multi_step_queries": multi_step_queries,
            "refined_query": refined_query,
            "processing_strategy": self._determine_strategy(complexity, intent, multi_step_queries)
        }

    def _analyze_complexity(self, query: str) -> QueryComplexity:
        """
        تحلیل پیچیدگی سوال
        """
        query_lower = query.lower()
        
        # نشانگرهای سوالات پیچیده
        complex_indicators = [
            "اگر", "چطور", "کدوم بهتره", "مقایسه", "تفاوت", "مزایا", "معایب",
            "برای", "مناسب", "پیشنهاد", "توصیه", "بهترین", "کیفیت"
        ]
        
        # نشانگرهای سوالات چندمرحله‌ای
        multi_step_indicators = [
            "هم", "و", "همچنین", "علاوه بر", "به اضافه", "همینطور", "و همچنین"
        ]
        
        complex_count = sum(1 for indicator in complex_indicators if indicator in query_lower)
        multi_step_count = sum(1 for indicator in multi_step_indicators if indicator in query_lower)
        
        if multi_step_count >= 2 or complex_count >= 3:
            return QueryComplexity.MULTI_STEP
        elif complex_count >= 2 or len(query.split()) > 15:
            return QueryComplexity.COMPLEX
        elif complex_count >= 1 or len(query.split()) > 8:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE

    def _extract_intent(self, query: str, chat_history: List[Dict] = None) -> QueryIntent:
        """
        استخراج intent از سوال
        """
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["مقایسه", "تفاوت", "کدوم بهتر", "مقایسه کن"]):
            return QueryIntent.COMPARE_PRODUCTS
        elif any(word in query_lower for word in ["پیشنهاد", "توصیه", "بهترین", "کیفیت"]):
            return QueryIntent.GET_RECOMMENDATIONS
        elif any(word in query_lower for word in ["بودجه", "قیمت", "ارزان", "گران", "هزینه"]):
            return QueryIntent.BUDGET_PLANNING
        elif any(word in query_lower for word in ["چطور", "چی", "چیه", "اطلاعات", "راهنمایی"]):
            return QueryIntent.GET_INFO
        elif any(word in query_lower for word in ["فیلتر", "بر اساس", "مطابق", "طبق"]):
            return QueryIntent.FILTER_PRODUCTS
        else:
            return QueryIntent.SEARCH_PRODUCT

    def _extract_entities(self, query: str) -> List[ExtractedEntity]:
        """
        استخراج entities از سوال
        """
        entities = []
        query_lower = query.lower()
        
        # استخراج دسته‌بندی محصولات
        category_patterns = {
            "کلاه کاسکت": ["کلاه", "کاسکت", "کلاه ایمنی", "helmet", "casco"],
            "پوشاک موتورسواری": ["دستکش", "کاپشن", "لباس", "پوشاک", "چکمه", "بوت"],
            "لاستیک موتور سیکلت": ["لاستیک", "تایر", "چرخ", "tire", "tyre"],
            "پروتکشن موتور سیکلت": ["پروتکشن", "محافظ", "زره", "protection"],
            "باکس موتور سیکلت": ["باکس", "جعبه", "صندوق", "box"],
            "لوازم جانبی موتورسیکلت": ["لوازم جانبی", "گردگیر", "لوازم"],
            "روغن موتور": ["روغن موتور", "engine oil", "motor oil"],
            "روغن ترمز": ["روغن ترمز", "brake fluid"]
        }
        
        for category, keywords in category_patterns.items():
            for keyword in keywords:
                if keyword in query_lower:
                    entities.append(ExtractedEntity(
                        type="category",
                        value=category,
                        confidence=0.9,
                        context=keyword
                    ))
                    break
        
        # استخراج برندها
        brand_patterns = [
            "state", "scoico", "agv", "shoei", "arai", "bell", "hjc", "ls2",
            "alpinestars", "dainese", "revit", "richa", "oxford", "spidi"
        ]
        
        for brand in brand_patterns:
            if brand in query_lower:
                entities.append(ExtractedEntity(
                    type="brand",
                    value=brand.title(),
                    confidence=0.8
                ))
        
        # استخراج سایزها
        size_patterns = re.findall(r'\b(xxs|xs|s|m|l|xl|xxl|xxxl)\b', query_lower)
        for size in size_patterns:
            entities.append(ExtractedEntity(
                type="size",
                value=size.upper(),
                confidence=0.9
            ))
        
        # استخراج ویژگی‌ها
        feature_keywords = [
            "سبک", "گرم", "سرد", "آب‌بند", "تنفس", "ضد آب", "ventilation",
            "ارگونومیک", "کربن", "carbon", "leather", "چرم"
        ]
        
        for feature in feature_keywords:
            if feature in query_lower:
                entities.append(ExtractedEntity(
                    type="feature",
                    value=feature,
                    confidence=0.7
                ))
        
        return entities

    def _extract_context(self, query: str, chat_history: List[Dict] = None) -> QueryContext:
        """
        استخراج context از سوال و تاریخچه
        """
        query_lower = query.lower()
        
        # استخراج فصل
        season = None
        for season_name, keywords in self.season_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                season = season_name
                break
        
        # استخراج نوع استفاده
        usage_type = None
        for usage, keywords in self.usage_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                usage_type = usage
                break
        
        # استخراج سطح تجربه
        experience_level = None
        for level, keywords in self.experience_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                experience_level = level
                break
        
        # استخراج فوریت
        urgency = "عادی"
        if any(word in query_lower for word in ["فوری", "سریع", "فوراً", "urgent"]):
            urgency = "فوری"
        
        # استخراج mentions قبلی از تاریخچه
        previous_mentions = []
        if chat_history:
            for message in chat_history[-5:]:  # آخرین 5 پیام
                content = message.get('content', '').lower()
                # استخراج محصولات، برندها و ویژگی‌های ذکر شده
                mentions = re.findall(r'\b[a-zA-Z]{3,}\b', content)
                previous_mentions.extend(mentions)
        
        return QueryContext(
            season=season,
            usage_type=usage_type,
            experience_level=experience_level,
            urgency=urgency,
            previous_mentions=previous_mentions[:10]  # حداکثر 10 mention
        )

    def _detect_multi_step(self, query: str, chat_history: List[Dict] = None) -> List[str]:
        """
        تشخیص سوالات چندمرحله‌ای
        """
        multi_step_queries = []
        
        # تشخیص سوالات ترکیبی با "و"
        if " و " in query:
            parts = query.split(" و ")
            multi_step_queries.extend([part.strip() for part in parts if part.strip()])
        
        # تشخیص سوالات شرطی
        if "اگر" in query and "چطور" in query:
            multi_step_queries.append("تحلیل شرطی")
        
        # تشخیص سوالات مقایسه‌ای
        if any(word in query.lower() for word in ["مقایسه", "تفاوت", "کدوم بهتر"]):
            multi_step_queries.append("مقایسه محصولات")
        
        return multi_step_queries

    def _refine_query(self, query: str, entities: List[ExtractedEntity], context: QueryContext) -> str:
        """
        بهبود و پالایش سوال
        """
        refined_parts = []
        
        # اضافه کردن context به query
        if context.season:
            refined_parts.append(f"مناسب برای {context.season}")
        
        if context.usage_type:
            refined_parts.append(f"برای استفاده {context.usage_type}")
        
        if context.experience_level:
            refined_parts.append(f"برای {context.experience_level}")
        
        # ترکیب query اصلی با context
        if refined_parts:
            refined_query = f"{query} ({', '.join(refined_parts)})"
        else:
            refined_query = query
        
        return refined_query

    def _determine_strategy(self, complexity: QueryComplexity, intent: QueryIntent, multi_step: List[str]) -> str:
        """
        تعیین استراتژی پردازش
        """
        if complexity == QueryComplexity.MULTI_STEP or multi_step:
            return "multi_step_processing"
        elif complexity == QueryComplexity.COMPLEX:
            return "complex_processing"
        elif intent == QueryIntent.COMPARE_PRODUCTS:
            return "comparison_processing"
        elif intent == QueryIntent.GET_RECOMMENDATIONS:
            return "recommendation_processing"
        else:
            return "standard_processing"

    def generate_follow_up_questions(self, entities: List[ExtractedEntity], context: QueryContext, intent: QueryIntent) -> List[str]:
        """
        تولید سوالات تکمیلی برای شفاف‌سازی
        """
        follow_ups = []
        
        # اگر دسته‌بندی مشخص نیست
        if not any(e.type == "category" for e in entities):
            follow_ups.append("چه نوع محصولی نیاز دارید؟ (کلاه کاسکت، دستکش، لاستیک، و...)")
        
        # اگر سایز مشخص نیست و محصول نیاز به سایز دارد
        if not any(e.type == "size" for e in entities):
            category_entities = [e for e in entities if e.type == "category"]
            if category_entities:
                follow_ups.append("سایز مورد نظر شما چیست؟ (S, M, L, XL, ...)")
        
        # اگر بودجه مشخص نیست
        if not re.search(r'\d+.*تومان|\d+.*تومن|\d+.*میلیون', " ".join([e.value for e in entities])):
            follow_ups.append("بودجه تقریبی شما چقدر است؟")
        
        # سوالات context-based
        if not context.season:
            follow_ups.append("برای چه فصلی از سال نیاز دارید؟")
        
        if not context.usage_type:
            follow_ups.append("برای چه نوع استفاده‌ای؟ (شهری، کراسی، مسافرتی)")
        
        return follow_ups[:3]  # حداکثر 3 سوال
