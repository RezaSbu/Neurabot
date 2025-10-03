from typing import Dict, List, Any, Optional, Tuple
import re
import json
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from app.config import settings
from app.memory.customer_profile import CustomerProfile

class QueryIntent(Enum):
    """انواع intent های مختلف query"""
    PURCHASE_READY = "purchase_ready"           # آماده خرید
    RESEARCH_PHASE = "research_phase"           # مرحله تحقیق
    COMPARISON_SEEKING = "comparison_seeking"   # جستجوی مقایسه
    TECHNICAL_SUPPORT = "technical_support"     # پشتیبانی فنی
    PRICE_INQUIRY = "price_inquiry"             # استعلام قیمت
    COMPATIBILITY_CHECK = "compatibility_check" # بررسی سازگاری
    GENERAL_BROWSING = "general_browsing"       # مرور عمومی

class CustomerSegment(Enum):
    """بخش‌بندی مشتریان"""
    PRICE_SENSITIVE = "price_sensitive"         # حساس به قیمت
    QUALITY_FOCUSED = "quality_focused"         # متمرکز بر کیفیت
    CONVENIENCE_SEEKER = "convenience_seeker"   # جویای راحتی
    TECH_ENTHUSIAST = "tech_enthusiast"         # علاقه‌مند به تکنولوژی
    BRAND_LOYAL = "brand_loyal"                 # وفادار به برند

class BusinessIntelligence:
    """سیستم هوش تجاری برای تحلیل و بهینه‌سازی"""
    
    def __init__(self):
        self.intent_patterns = self._initialize_intent_patterns()
        self.segment_rules = self._initialize_segment_rules()
        self.business_rules = self._initialize_business_rules()

    async def analyze_query_intent(
        self, 
        query: str, 
        context: Dict[str, Any],
        user_profile: Optional[CustomerProfile] = None
    ) -> Dict[str, Any]:
        """تحلیل عمیق intent کاربر"""
        
        query_lower = query.lower()
        intent_scores = {}
        
        # تحلیل الگوهای متنی
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            
            # بررسی کلمات کلیدی
            for pattern_type, keywords in patterns.items():
                if pattern_type == "keywords":
                    matches = sum(1 for keyword in keywords if keyword in query_lower)
                    score += matches * 0.2
                elif pattern_type == "phrases":
                    matches = sum(1 for phrase in keywords if phrase in query_lower)
                    score += matches * 0.3
                elif pattern_type == "patterns":
                    for regex_pattern in keywords:
                        if re.search(regex_pattern, query_lower):
                            score += 0.4
            
            intent_scores[intent.value] = min(1.0, score)
        
        # تعدیل بر اساس context
        intent_scores = self._adjust_intent_by_context(intent_scores, context)
        
        # تعدیل بر اساس پروفایل کاربر
        if user_profile:
            intent_scores = self._adjust_intent_by_profile(intent_scores, user_profile)
        
        # تعیین intent اصلی
        primary_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[primary_intent]
        
        # تعیین intent های ثانویه
        secondary_intents = sorted(
            [(intent, score) for intent, score in intent_scores.items() 
             if intent != primary_intent and score > 0.3],
            key=lambda x: x[1], reverse=True
        )[:2]
        
        return {
            "primary_intent": primary_intent,
            "confidence": round(confidence, 3),
            "secondary_intents": dict(secondary_intents),
            "all_scores": intent_scores,
            "analysis_factors": self._get_analysis_factors(query, context, user_profile),
            "recommended_approach": self._get_recommended_approach(primary_intent, confidence),
            "urgency_level": self._assess_urgency(query, context, user_profile)
        }

    def _initialize_intent_patterns(self) -> Dict[QueryIntent, Dict[str, List[str]]]:
        """مقداردهی الگوهای intent"""
        return {
            QueryIntent.PURCHASE_READY: {
                "keywords": ["می‌خوام", "بخرم", "سفارش", "خرید", "قیمت نهایی", "موجود"],
                "phrases": ["چقدر می‌شه", "کجا بخرم", "قیمت چنده", "الان می‌خوام"],
                "patterns": [r"تا\s+(\d+)\s+(تومان|میلیون)", r"بودجه\s+دارم", r"فوری\s+نیاز"]
            },
            QueryIntent.RESEARCH_PHASE: {
                "keywords": ["بررسی", "مقایسه", "راهنمایی", "مشورت", "نظر", "تجربه"],
                "phrases": ["چی بهتره", "کدوم رو انتخاب کنم", "راجع به", "در مورد"],
                "patterns": [r"چه\s+فرقی", r"مزایا\s+و\s+معایب", r"بهترین\s+انتخاب"]
            },
            QueryIntent.COMPARISON_SEEKING: {
                "keywords": ["مقایسه", "تفاوت", "فرق", "بهتر", "برتر", "انتخاب"],
                "phrases": ["در مقابل", "نسبت به", "یا", "بین", "کدام بهتر"],
                "patterns": [r"(\w+)\s+یا\s+(\w+)", r"مقایسه\s+(\w+)", r"فرق\s+(\w+)\s+با"]
            },
            QueryIntent.TECHNICAL_SUPPORT: {
                "keywords": ["نصب", "راه‌اندازی", "مشکل", "خرابی", "تعمیر", "نگهداری"],
                "phrases": ["چطور نصب کنم", "مشکل دارم", "کار نمی‌کنه", "راهنمایی نصب"],
                "patterns": [r"چطور\s+(\w+)", r"مشکل\s+(\w+)", r"نحوه\s+(\w+)"]
            },
            QueryIntent.PRICE_INQUIRY: {
                "keywords": ["قیمت", "هزینه", "تومان", "میلیون", "ارزان", "گران"],
                "phrases": ["چقدر قیمت", "قیمت چنده", "چقدر می‌شه", "هزینه چقدر"],
                "patterns": [r"قیمت\s+(\w+)", r"(\d+)\s+تومان", r"چقدر\s+هزینه"]
            },
            QueryIntent.COMPATIBILITY_CHECK: {
                "keywords": ["سازگار", "مناسب", "متناسب", "compatibility", "مدل", "موتور"],
                "phrases": ["مناسب موتور", "سازگار با", "برای موتور", "روی موتور"],
                "patterns": [r"برای\s+(\w+)\s+مناسب", r"با\s+(\w+)\s+سازگار", r"روی\s+(\w+)"]
            },
            QueryIntent.GENERAL_BROWSING: {
                "keywords": ["نشون بده", "ببینم", "دارید", "موجود", "کالا", "محصول"],
                "phrases": ["چه چیزی دارید", "محصولاتتون", "کالاهاتون", "چی موجوده"],
                "patterns": [r"لیست\s+(\w+)", r"انواع\s+(\w+)", r"همه\s+(\w+)"]
            }
        }

    def _adjust_intent_by_context(
        self, 
        intent_scores: Dict[str, float], 
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """تعدیل intent بر اساس context"""
        
        # اگر در تاریخچه مکالمه قیمت پرسیده شده، احتمال خرید بالا می‌رود
        conversation_history = context.get('conversation_history', [])
        if conversation_history:
            recent_messages = ' '.join([msg.get('content', '') for msg in conversation_history[-3:]])
            if any(word in recent_messages.lower() for word in ['قیمت', 'چقدر', 'هزینه']):
                intent_scores[QueryIntent.PURCHASE_READY.value] += 0.2
        
        # اگر زمان روز اوج خرید است
        current_hour = datetime.now().hour
        if 10 <= current_hour <= 22:  # ساعات فعال خرید
            intent_scores[QueryIntent.PURCHASE_READY.value] += 0.1
        
        # اگر روز آخر هفته است (احتمال خرید بیشتر)
        if datetime.now().weekday() >= 4:  # جمعه و شنبه
            intent_scores[QueryIntent.PURCHASE_READY.value] += 0.1
        
        return intent_scores

    def _adjust_intent_by_profile(
        self, 
        intent_scores: Dict[str, float], 
        user_profile: CustomerProfile
    ) -> Dict[str, float]:
        """تعدیل intent بر اساس پروفایل کاربر"""
        
        # مشتریان وفادار احتمال خرید بیشتری دارند
        if user_profile.customer_type == "loyal":
            intent_scores[QueryIntent.PURCHASE_READY.value] += 0.3
        elif user_profile.customer_type == "returning":
            intent_scores[QueryIntent.PURCHASE_READY.value] += 0.2
        
        # مشتریان با حساسیت قیمت بالا بیشتر تحقیق می‌کنند
        if user_profile.price_sensitivity == "high":
            intent_scores[QueryIntent.RESEARCH_PHASE.value] += 0.2
            intent_scores[QueryIntent.COMPARISON_SEEKING.value] += 0.2
        
        # مشتریان متخصص بیشتر دنبال جزئیات فنی هستند
        if user_profile.technical_expertise == "expert":
            intent_scores[QueryIntent.TECHNICAL_SUPPORT.value] += 0.2
        
        # اگر اخیراً خرید کرده، کمتر احتمال خرید مجدد دارد
        if user_profile.previous_purchases:
            last_purchase = user_profile.previous_purchases[-1]
            last_purchase_date = datetime.fromisoformat(last_purchase.get('purchase_date', '2020-01-01'))
            days_since_purchase = (datetime.now() - last_purchase_date).days
            
            if days_since_purchase < 7:  # کمتر از یک هفته
                intent_scores[QueryIntent.PURCHASE_READY.value] -= 0.2
        
        return intent_scores

    def _get_analysis_factors(
        self, 
        query: str, 
        context: Dict[str, Any], 
        user_profile: Optional[CustomerProfile]
    ) -> List[str]:
        """استخراج عوامل تأثیرگذار در تحلیل"""
        factors = []
        
        # عوامل متنی
        if any(word in query.lower() for word in ['فوری', 'سریع', 'الان']):
            factors.append("فوریت بالا")
        
        if any(word in query.lower() for word in ['بودجه', 'تومان', 'قیمت']):
            factors.append("حساسیت قیمت")
        
        if any(word in query.lower() for word in ['بهترین', 'برترین', 'کیفیت']):
            factors.append("تمرکز بر کیفیت")
        
        # عوامل پروفایل
        if user_profile:
            if user_profile.customer_type != "new":
                factors.append(f"مشتری {user_profile.customer_type}")
            
            if user_profile.technical_expertise != "beginner":
                factors.append(f"تخصص {user_profile.technical_expertise}")
            
            if user_profile.motorcycle_model:
                factors.append(f"موتور {user_profile.motorcycle_model}")
        
        # عوامل زمانی
        current_hour = datetime.now().hour
        if 10 <= current_hour <= 14:
            factors.append("ساعات اوج خرید")
        elif 20 <= current_hour <= 22:
            factors.append("ساعات عصر")
        
        return factors

    def _get_recommended_approach(self, intent: str, confidence: float) -> Dict[str, Any]:
        """تعیین رویکرد توصیه شده"""
        approaches = {
            QueryIntent.PURCHASE_READY.value: {
                "strategy": "direct_sales",
                "focus": "محصولات موجود با قیمت شفاف",
                "tools": ["QueryKnowledgeBaseTool", "StockAnalyticsTool"],
                "response_style": "قاطع و فروش‌محور"
            },
            QueryIntent.RESEARCH_PHASE.value: {
                "strategy": "educational",
                "focus": "اطلاعات جامع و مقایسه",
                "tools": ["ProductComparisonTool", "QueryKnowledgeBaseTool"],
                "response_style": "آموزشی و مشورتی"
            },
            QueryIntent.COMPARISON_SEEKING.value: {
                "strategy": "comparative_analysis",
                "focus": "مقایسه دقیق محصولات",
                "tools": ["ProductComparisonTool"],
                "response_style": "تحلیلی و بی‌طرف"
            },
            QueryIntent.TECHNICAL_SUPPORT.value: {
                "strategy": "problem_solving",
                "focus": "راه‌حل‌های فنی",
                "tools": ["CompatibilityCheckTool", "QueryKnowledgeBaseTool"],
                "response_style": "فنی و راه‌حل‌محور"
            },
            QueryIntent.COMPATIBILITY_CHECK.value: {
                "strategy": "compatibility_focus",
                "focus": "بررسی سازگاری دقیق",
                "tools": ["CompatibilityCheckTool"],
                "response_style": "دقیق و فنی"
            },
            QueryIntent.GENERAL_BROWSING.value: {
                "strategy": "general_exploration",
                "focus": "نمایش محصولات متنوع",
                "tools": ["QueryKnowledgeBaseTool", "StockAnalyticsTool"],
                "response_style": "دوستانه و راهنما"
            }
        }
        
        base_approach = approaches.get(intent, approaches[QueryIntent.GENERAL_BROWSING.value])
        
        # تعدیل بر اساس اعتماد
        if confidence < 0.5:
            base_approach["strategy"] = "cautious_exploration"
            base_approach["response_style"] = "کاوشگر و سوال‌محور"
        
        base_approach["confidence_level"] = confidence
        return base_approach

    def _assess_urgency(
        self, 
        query: str, 
        context: Dict[str, Any], 
        user_profile: Optional[CustomerProfile]
    ) -> str:
        """ارزیابی سطح فوریت"""
        urgency_score = 0
        
        # کلمات فوری
        urgent_keywords = ['فوری', 'سریع', 'الان', 'امروز', 'زودتر', 'عجله']
        urgency_score += sum(1 for keyword in urgent_keywords if keyword in query.lower())
        
        # موجودی کم
        if 'موجودی کم' in context.get('stock_alerts', []):
            urgency_score += 2
        
        # مشتری VIP
        if user_profile and user_profile.customer_type in ["loyal", "premium"]:
            urgency_score += 1
        
        # تعیین سطح فوریت
        if urgency_score >= 3:
            return "high"
        elif urgency_score >= 1:
            return "medium"
        else:
            return "low"

    async def optimize_product_mix(
        self, 
        base_results: List[Dict[str, Any]], 
        user_profile: Optional[CustomerProfile],
        business_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """بهینه‌سازی ترکیب محصولات برای فروش بهتر"""
        
        if not base_results:
            return base_results
        
        optimized_results = []
        
        for result in base_results:
            metadata = result.get('metadata', {})
            
            # محاسبه امتیاز تجاری
            business_score = self._calculate_business_optimization_score(
                metadata, user_profile, business_context
            )
            
            # اضافه کردن اطلاعات بهینه‌سازی
            result['business_optimization'] = {
                'score': business_score,
                'profit_margin': self._estimate_profit_margin(metadata),
                'inventory_priority': self._get_inventory_priority(metadata),
                'cross_sell_potential': self._assess_cross_sell_potential(metadata, user_profile),
                'customer_fit': self._assess_customer_fit(metadata, user_profile)
            }
            
            optimized_results.append(result)
        
        # مرتب‌سازی بر اساس امتیاز بهینه‌سازی تجاری
        return sorted(
            optimized_results, 
            key=lambda x: x['business_optimization']['score'], 
            reverse=True
        )

    def _calculate_business_optimization_score(
        self, 
        metadata: Dict[str, Any], 
        user_profile: Optional[CustomerProfile],
        business_context: Dict[str, Any]
    ) -> float:
        """محاسبه امتیاز بهینه‌سازی تجاری"""
        score = 0.0
        
        # امتیاز سود
        profit_margin = self._estimate_profit_margin(metadata)
        score += profit_margin * 0.3
        
        # امتیاز موجودی
        inventory_score = self._get_inventory_score(metadata)
        score += inventory_score * 0.2
        
        # امتیاز تناسب با مشتری
        if user_profile:
            customer_fit = self._assess_customer_fit(metadata, user_profile)
            score += customer_fit * 0.3
        
        # امتیاز پتانسیل فروش متقابل
        cross_sell_score = self._assess_cross_sell_potential(metadata, user_profile)
        score += cross_sell_score * 0.2
        
        return min(1.0, score)

    def _estimate_profit_margin(self, metadata: Dict[str, Any]) -> float:
        """تخمین حاشیه سود (بر اساس قیمت و برند)"""
        price = metadata.get('price_numeric', 0)
        brand = metadata.get('brand', '').lower()
        
        # حاشیه سود تخمینی بر اساس برند
        brand_margins = {
            'yamaha': 0.15, 'honda': 0.15, 'suzuki': 0.18, 'kawasaki': 0.18,
            'mt': 0.25, 'smk': 0.30, 'soman': 0.25, 'scoyco': 0.35,
            'fulmer': 0.40, 'beon': 0.35, 'qike': 0.45, 'redline': 0.50,
            'ردلاین': 0.50, 'ایران یاسا': 0.40, 'نامشخص': 0.30
        }
        
        base_margin = brand_margins.get(brand, 0.30)
        
        # تعدیل بر اساس قیمت
        if price > 15000000:  # محصولات گران معمولاً حاشیه کمتری دارند
            return base_margin * 0.8
        elif price < 2000000:  # محصولات ارزان ممکن است حاشیه بیشتری داشته باشند
            return min(0.6, base_margin * 1.2)
        
        return base_margin

    def _get_inventory_score(self, metadata: Dict[str, Any]) -> float:
        """امتیاز موجودی (موجودی کم = امتیاز بالا برای فروش)"""
        stock = metadata.get('stock', '')
        
        if 'ناموجود' in stock:
            return 0.0
        elif any(char.isdigit() and int(char) <= 2 for char in stock):
            return 1.0  # موجودی کم - اولویت فروش
        elif any(char.isdigit() and int(char) <= 5 for char in stock):
            return 0.7
        else:
            return 0.3  # موجودی زیاد

    def _get_inventory_priority(self, metadata: Dict[str, Any]) -> str:
        """اولویت موجودی"""
        stock = metadata.get('stock', '')
        
        if 'ناموجود' in stock:
            return "unavailable"
        elif any(char.isdigit() and int(char) <= 2 for char in stock):
            return "urgent"  # نیاز فوری به فروش
        elif any(char.isdigit() and int(char) <= 5 for char in stock):
            return "high"
        else:
            return "normal"

    def _assess_cross_sell_potential(
        self, 
        metadata: Dict[str, Any], 
        user_profile: Optional[CustomerProfile]
    ) -> float:
        """ارزیابی پتانسیل فروش متقابل"""
        category = metadata.get('category', '').lower()
        
        # دسته‌هایی که پتانسیل cross-sell بالایی دارند
        high_cross_sell_categories = [
            'کلاه کاسکت', 'پوشاک موتورسواری', 'لاستیک موتور سیکلت'
        ]
        
        if any(cat in category for cat in high_cross_sell_categories):
            base_score = 0.8
        else:
            base_score = 0.4
        
        # تعدیل بر اساس پروفایل کاربر
        if user_profile:
            # اگر مشتری تاریخچه خرید متنوعی دارد
            if len(user_profile.previous_purchases) > 2:
                base_score += 0.2
            
            # اگر مشتری قبلاً محصولات مکمل خریده
            purchased_categories = [p.get('category', '') for p in user_profile.previous_purchases]
            if len(set(purchased_categories)) > 1:
                base_score += 0.1
        
        return min(1.0, base_score)

    def _assess_customer_fit(
        self, 
        metadata: Dict[str, Any], 
        user_profile: Optional[CustomerProfile]
    ) -> float:
        """ارزیابی تناسب با مشتری"""
        if not user_profile:
            return 0.5
        
        fit_score = 0.0
        
        # تناسب برند
        brand = metadata.get('brand', '')
        if brand in user_profile.preferred_brands:
            fit_score += 0.3
        elif brand in user_profile.avoided_brands:
            fit_score -= 0.2
        
        # تناسب قیمت
        price = metadata.get('price_numeric', 0)
        if user_profile.budget_range:
            price_filter = user_profile.get_price_filter_suggestion()
            if price_filter:
                min_price = price_filter.get('min', 0)
                max_price = price_filter.get('max', float('inf'))
                if min_price <= price <= max_price:
                    fit_score += 0.3
                else:
                    fit_score -= 0.1
        
        # تناسب دسته‌بندی
        category = metadata.get('category', '')
        if user_profile.purchase_patterns.get('favorite_categories'):
            favorite_cats = [cat[0] for cat in user_profile.purchase_patterns['favorite_categories']]
            if category in favorite_cats:
                fit_score += 0.2
        
        # تناسب سطح تخصص
        features = metadata.get('features_flat', '').lower()
        if user_profile.technical_expertise == "expert" and 'حرفه‌ای' in features:
            fit_score += 0.1
        elif user_profile.technical_expertise == "beginner" and 'آسان' in features:
            fit_score += 0.1
        
        return max(0.0, min(1.0, fit_score + 0.5))  # base score 0.5

    async def predict_customer_lifetime_value(
        self, 
        user_profile: CustomerProfile
    ) -> Dict[str, Any]:
        """پیش‌بینی ارزش مشتری در طول زندگی"""
        
        # محاسبه CLV بر اساس الگوهای خرید
        purchase_history = user_profile.previous_purchases
        
        if not purchase_history:
            return {
                "predicted_clv": 0,
                "confidence": "low",
                "segment": "new_customer",
                "recommendations": ["تشویق به اولین خرید"]
            }
        
        # محاسبه متریک‌های پایه
        total_spent = sum(p.get('price', 0) for p in purchase_history)
        purchase_count = len(purchase_history)
        avg_order_value = total_spent / purchase_count if purchase_count > 0 else 0
        
        # محاسبه فرکانس خرید
        if purchase_count > 1:
            first_purchase = datetime.fromisoformat(purchase_history[0]['purchase_date'])
            last_purchase = datetime.fromisoformat(purchase_history[-1]['purchase_date'])
            days_active = (last_purchase - first_purchase).days
            purchase_frequency = purchase_count / max(days_active / 30, 1)  # خرید در ماه
        else:
            purchase_frequency = 0.1  # تخمین برای مشتری جدید
        
        # پیش‌بینی CLV (فرمول ساده)
        predicted_months_active = min(24, max(6, purchase_frequency * 12))
        predicted_clv = avg_order_value * purchase_frequency * predicted_months_active
        
        # تعیین segment
        if predicted_clv > 50000000:  # بالای 50 میلیون
            segment = "high_value"
        elif predicted_clv > 20000000:  # 20-50 میلیون
            segment = "medium_value"
        elif predicted_clv > 5000000:  # 5-20 میلیون
            segment = "regular"
        else:
            segment = "low_value"
        
        # تعیین سطح اعتماد
        if purchase_count >= 5:
            confidence = "high"
        elif purchase_count >= 2:
            confidence = "medium"
        else:
            confidence = "low"
        
        # تولید توصیه‌ها
        recommendations = self._generate_clv_recommendations(segment, user_profile)
        
        return {
            "predicted_clv": int(predicted_clv),
            "avg_order_value": int(avg_order_value),
            "purchase_frequency": round(purchase_frequency, 2),
            "predicted_lifetime_months": int(predicted_months_active),
            "confidence": confidence,
            "segment": segment,
            "recommendations": recommendations,
            "risk_factors": self._identify_churn_risks(user_profile)
        }

    def _generate_clv_recommendations(
        self, 
        segment: str, 
        user_profile: CustomerProfile
    ) -> List[str]:
        """تولید توصیه‌ها بر اساس CLV"""
        recommendations = []
        
        if segment == "high_value":
            recommendations.extend([
                "ارائه تخفیف VIP",
                "دعوت به برنامه وفاداری",
                "پیشنهاد محصولات پریمیوم",
                "خدمات شخصی‌سازی شده"
            ])
        elif segment == "medium_value":
            recommendations.extend([
                "پیشنهاد bundle های جذاب",
                "تخفیف برای خرید بعدی",
                "ارسال پیشنهادات منظم"
            ])
        elif segment == "regular":
            recommendations.extend([
                "تشویق به خرید بیشتر",
                "معرفی محصولات مکمل",
                "ایجاد حس فوریت"
            ])
        else:  # low_value
            recommendations.extend([
                "تمرکز بر محصولات اقتصادی",
                "تخفیف‌های جذاب",
                "آموزش ارزش محصولات"
            ])
        
        return recommendations

    def _identify_churn_risks(self, user_profile: CustomerProfile) -> List[str]:
        """شناسایی ریسک‌های ترک مشتری"""
        risks = []
        
        # عدم خرید اخیر
        if user_profile.previous_purchases:
            last_purchase = datetime.fromisoformat(
                user_profile.previous_purchases[-1]['purchase_date']
            )
            days_since_last = (datetime.now() - last_purchase).days
            
            if days_since_last > 180:  # 6 ماه
                risks.append("عدم خرید طولانی‌مدت")
            elif days_since_last > 90:  # 3 ماه
                risks.append("کاهش فعالیت خرید")
        
        # حساسیت بالا به قیمت
        if user_profile.price_sensitivity == "high":
            risks.append("حساسیت بالا به قیمت")
        
        # عدم تنوع در خرید
        if len(user_profile.previous_purchases) > 3:
            categories = set(p.get('category') for p in user_profile.previous_purchases)
            if len(categories) == 1:
                risks.append("عدم تنوع در خرید")
        
        return risks

    def _initialize_segment_rules(self) -> Dict[CustomerSegment, Dict[str, Any]]:
        """مقداردهی قوانین بخش‌بندی مشتریان"""
        return {
            CustomerSegment.PRICE_SENSITIVE: {
                "indicators": ["ارزان", "قیمت پایین", "تخفیف", "اقتصادی"],
                "behavior_patterns": ["مقایسه قیمت", "جستجوی تخفیف"],
                "response_strategy": "تأکید بر ارزش و صرفه‌جویی"
            },
            CustomerSegment.QUALITY_FOCUSED: {
                "indicators": ["کیفیت", "برند معتبر", "بهترین", "دوام"],
                "behavior_patterns": ["تحقیق دقیق", "مقایسه ویژگی‌ها"],
                "response_strategy": "تأکید بر کیفیت و مزایای فنی"
            },
            CustomerSegment.CONVENIENCE_SEEKER: {
                "indicators": ["آسان", "سریع", "راحت", "بدون دردسر"],
                "behavior_patterns": ["خرید سریع", "اجتناب از پیچیدگی"],
                "response_strategy": "تأکید بر سادگی و راحتی"
            },
            CustomerSegment.TECH_ENTHUSIAST: {
                "indicators": ["فنی", "پیشرفته", "تکنولوژی", "نوآوری"],
                "behavior_patterns": ["جستجوی جزئیات فنی", "علاقه به جدیدترین‌ها"],
                "response_strategy": "ارائه اطلاعات فنی دقیق"
            },
            CustomerSegment.BRAND_LOYAL: {
                "indicators": ["برند خاص", "همیشه", "فقط", "وفادار"],
                "behavior_patterns": ["تکرار برند", "مقاومت در برابر تغییر"],
                "response_strategy": "تقویت وفاداری و معرفی محصولات همان برند"
            }
        }

    def _initialize_business_rules(self) -> Dict[str, Any]:
        """مقداردهی قوانین تجاری"""
        return {
            "inventory_management": {
                "low_stock_threshold": settings.STOCK_ALERT_THRESHOLD,
                "high_priority_categories": ["کلاه کاسکت", "لاستیک موتور سیکلت"],
                "seasonal_adjustments": {
                    "winter": ["پوشاک موتورسواری", "دستکش"],
                    "summer": ["کلاه کاسکت", "لوازم جانبی"]
                }
            },
            "pricing_strategy": {
                "premium_brands": ["yamaha", "honda", "suzuki", "kawasaki"],
                "value_brands": ["mt", "smk", "soman"],
                "budget_brands": ["fulmer", "beon", "qike", "redline"]
            },
            "cross_sell_rules": {
                "mandatory_combinations": {
                    "کلاه کاسکت": ["دستکش"],
                    "لاستیک موتور سیکلت": ["تیوب"]
                },
                "suggested_combinations": {
                    "پوشاک موتورسواری": ["کلاه کاسکت", "دستکش", "پروتکشن"],
                    "باکس موتور سیکلت": ["قفل", "بند"]
                }
            }
        }
