from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import re
from app.config import settings

class CustomerProfile(BaseModel):
    """پروفایل هوشمند مشتری برای شخصی‌سازی تجربه خرید"""
    
    session_id: str
    motorcycle_model: Optional[str] = None
    riding_style: Optional[str] = None  # city, sport, touring, off-road, mixed
    budget_range: Optional[str] = None  # "زیر ۵ میلیون", "۵-۱۰ میلیون", etc.
    preferred_brands: List[str] = Field(default_factory=list)
    avoided_brands: List[str] = Field(default_factory=list)
    previous_purchases: List[Dict[str, Any]] = Field(default_factory=list)
    browsing_history: List[Dict[str, Any]] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    customer_type: str = "new"  # new, returning, loyal, premium
    price_sensitivity: str = "medium"  # low, medium, high
    technical_expertise: str = "beginner"  # beginner, intermediate, expert
    purchase_patterns: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    async def update_from_conversation(self, messages: List[Dict[str, str]], rdb) -> None:
        """استخراج و به‌روزرسانی اطلاعات مشتری از مکالمه"""
        
        # ترکیب تمام پیام‌های کاربر
        user_messages = [msg['content'] for msg in messages if msg.get('role') == 'user']
        conversation_text = ' '.join(user_messages).lower()
        
        # استخراج مدل موتور
        self._extract_motorcycle_model(conversation_text)
        
        # تشخیص سبک رانندگی
        self._detect_riding_style(conversation_text)
        
        # استخراج بودجه
        self._extract_budget_range(conversation_text)
        
        # تشخیص برندهای ترجیحی
        self._detect_brand_preferences(conversation_text)
        
        # تحلیل سطح تخصص
        self._analyze_technical_expertise(conversation_text)
        
        # تشخیص حساسیت قیمت
        self._detect_price_sensitivity(conversation_text)
        
        # به‌روزرسانی تاریخ
        self.last_updated = datetime.now()
        
        # ذخیره در Redis
        await self._save_to_redis(rdb)

    def _extract_motorcycle_model(self, text: str) -> None:
        """استخراج مدل موتور از متن"""
        motorcycle_patterns = [
            r'موتور\s+(\w+)',
            r'(\w+)\s+دارم',
            r'برای\s+(\w+)\s+می‌خوام',
            r'(\w+)\s+سوار\s+می‌کنم'
        ]
        
        known_models = [
            'کلیک', 'آیروکس', 'هیوسانگ', 'آپاچی', 'بنلی', 'پولسار', 
            'کاوازاکی', 'یاماها', 'هوندا', 'سوزوکی', 'هارلی'
        ]
        
        for pattern in motorcycle_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if any(model.lower() in match.lower() for model in known_models):
                    self.motorcycle_model = match
                    break
            if self.motorcycle_model:
                break

    def _detect_riding_style(self, text: str) -> None:
        """تشخیص سبک رانندگی"""
        style_indicators = {
            'city': ['شهری', 'شهر', 'ترافیک', 'کار', 'روزانه', 'معمولی'],
            'sport': ['اسپرت', 'سریع', 'مسابقه', 'سرعت', 'پیست'],
            'touring': ['مسافرت', 'طولانی', 'جاده', 'سفر', 'ادونچر'],
            'off-road': ['آفرود', 'کراس', 'کوهستان', 'خاکی', 'صحرا'],
            'mixed': ['مختلط', 'همه کاره', 'گاهی', 'بعضی وقت‌ها']
        }
        
        style_scores = {}
        for style, keywords in style_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                style_scores[style] = score
        
        if style_scores:
            self.riding_style = max(style_scores, key=style_scores.get)

    def _extract_budget_range(self, text: str) -> None:
        """استخراج محدوده بودجه"""
        budget_patterns = [
            r'تا\s+(\d+)\s*(میلیون|تومان|تومن)',
            r'حدود\s+(\d+)\s*(میلیون|تومان|تومن)',
            r'بودجه\s+(\d+)\s*(میلیون|تومان|تومن)',
            r'(\d+)\s*(میلیون|تومان|تومن)\s+دارم'
        ]
        
        for pattern in budget_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                amount, unit = match
                amount = int(amount)
                
                if unit in ['تومان', 'تومن']:
                    if amount <= 10:  # مثلاً 5 تومان = 5 میلیون تومان
                        amount *= 1000000
                    elif amount <= 1000:  # مثلاً 500 تومان = 500 هزار تومان
                        amount *= 1000
                elif unit == 'میلیون':
                    amount *= 1000000
                
                # تعیین محدوده بودجه
                if amount < 5000000:
                    self.budget_range = "زیر ۵ میلیون"
                elif amount < 10000000:
                    self.budget_range = "۵-۱۰ میلیون"
                elif amount < 20000000:
                    self.budget_range = "۱۰-۲۰ میلیون"
                else:
                    self.budget_range = "بیش از ۲۰ میلیون"
                break
            if self.budget_range:
                break

    def _detect_brand_preferences(self, text: str) -> None:
        """تشخیص برندهای ترجیحی و غیرترجیحی"""
        known_brands = [
            'یاماها', 'هوندا', 'سوزوکی', 'کاوازاکی', 'MT', 'SMK', 'SOMAN', 
            'SCOYCO', 'FULMER', 'BEON', 'QIKE', 'REDLINE', 'ردلاین', 'ایران یاسا'
        ]
        
        positive_indicators = ['دوست دارم', 'ترجیح می‌دم', 'خوب', 'عالی', 'مناسب']
        negative_indicators = ['دوست ندارم', 'بد', 'مناسب نیست', 'نمی‌خوام']
        
        for brand in known_brands:
            brand_lower = brand.lower()
            if brand_lower in text:
                # بررسی context برای تشخیص نظر
                brand_context = self._get_brand_context(text, brand_lower)
                
                if any(indicator in brand_context for indicator in positive_indicators):
                    if brand not in self.preferred_brands:
                        self.preferred_brands.append(brand)
                elif any(indicator in brand_context for indicator in negative_indicators):
                    if brand not in self.avoided_brands:
                        self.avoided_brands.append(brand)

    def _get_brand_context(self, text: str, brand: str) -> str:
        """استخراج context اطراف نام برند"""
        brand_index = text.find(brand)
        if brand_index == -1:
            return ""
        
        start = max(0, brand_index - 50)
        end = min(len(text), brand_index + len(brand) + 50)
        return text[start:end]

    def _analyze_technical_expertise(self, text: str) -> None:
        """تحلیل سطح دانش فنی مشتری"""
        expert_terms = [
            'پهنا', 'پروفایل', 'رینگ', 'سی‌سی', 'کاربراتور', 'انژکتور',
            'سوپاپ', 'پیستون', 'گیربکس', 'کلاچ', 'ترمز دیسکی'
        ]
        
        beginner_terms = [
            'نمی‌دونم', 'چیه', 'چطور', 'راهنمایی', 'کمک', 'نمی‌فهمم'
        ]
        
        expert_score = sum(1 for term in expert_terms if term in text)
        beginner_score = sum(1 for term in beginner_terms if term in text)
        
        if expert_score >= 3:
            self.technical_expertise = "expert"
        elif expert_score >= 1 and beginner_score == 0:
            self.technical_expertise = "intermediate"
        else:
            self.technical_expertise = "beginner"

    def _detect_price_sensitivity(self, text: str) -> None:
        """تشخیص حساسیت قیمت"""
        price_sensitive_terms = [
            'ارزان', 'قیمت پایین', 'کم هزینه', 'اقتصادی', 'بودجه محدود'
        ]
        
        price_insensitive_terms = [
            'کیفیت', 'بهترین', 'برند معتبر', 'مهم نیست', 'قیمت مهم نیست'
        ]
        
        sensitive_score = sum(1 for term in price_sensitive_terms if term in text)
        insensitive_score = sum(1 for term in price_insensitive_terms if term in text)
        
        if sensitive_score > insensitive_score:
            self.price_sensitivity = "high"
        elif insensitive_score > sensitive_score:
            self.price_sensitivity = "low"
        else:
            self.price_sensitivity = "medium"

    def add_purchase(self, product_info: Dict[str, Any]) -> None:
        """اضافه کردن خرید به تاریخچه"""
        purchase = {
            "product_id": product_info.get("product_id"),
            "name": product_info.get("name"),
            "category": product_info.get("category"),
            "brand": product_info.get("brand"),
            "price": product_info.get("price_numeric", 0),
            "purchase_date": datetime.now().isoformat()
        }
        
        self.previous_purchases.append(purchase)
        
        # به‌روزرسانی الگوهای خرید
        self._update_purchase_patterns()

    def add_browsing_activity(self, activity: Dict[str, Any]) -> None:
        """اضافه کردن فعالیت مرور به تاریخچه"""
        browsing_record = {
            "query": activity.get("query"),
            "category": activity.get("category"),
            "products_viewed": activity.get("products", []),
            "timestamp": datetime.now().isoformat()
        }
        
        self.browsing_history.append(browsing_record)
        
        # نگه داشتن فقط 50 رکورد آخر
        if len(self.browsing_history) > 50:
            self.browsing_history = self.browsing_history[-50:]

    def _update_purchase_patterns(self) -> None:
        """به‌روزرسانی الگوهای خرید"""
        if not self.previous_purchases:
            return
        
        # تحلیل دسته‌های محبوب
        categories = {}
        brands = {}
        total_spent = 0
        
        for purchase in self.previous_purchases:
            category = purchase.get("category", "نامشخص")
            brand = purchase.get("brand", "نامشخص")
            price = purchase.get("price", 0)
            
            categories[category] = categories.get(category, 0) + 1
            brands[brand] = brands.get(brand, 0) + 1
            total_spent += price
        
        self.purchase_patterns = {
            "favorite_categories": sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3],
            "favorite_brands": sorted(brands.items(), key=lambda x: x[1], reverse=True)[:3],
            "total_spent": total_spent,
            "average_purchase": total_spent / len(self.previous_purchases) if self.previous_purchases else 0,
            "purchase_frequency": len(self.previous_purchases)
        }
        
        # تعیین نوع مشتری
        if len(self.previous_purchases) >= 5:
            self.customer_type = "loyal"
        elif len(self.previous_purchases) >= 2:
            self.customer_type = "returning"
        elif total_spent > 20000000:  # بالای 20 میلیون
            self.customer_type = "premium"
        else:
            self.customer_type = "new"

    async def get_personalized_recommendations(self, rdb) -> Dict[str, Any]:
        """تولید توصیه‌های شخصی‌سازی شده"""
        recommendations = {
            "preferred_categories": [],
            "suggested_brands": [],
            "price_range_focus": self.budget_range,
            "compatibility_focus": self.motorcycle_model,
            "personalization_factors": []
        }
        
        # توصیه بر اساس تاریخچه خرید
        if self.purchase_patterns.get("favorite_categories"):
            recommendations["preferred_categories"] = [
                cat[0] for cat in self.purchase_patterns["favorite_categories"]
            ]
            recommendations["personalization_factors"].append("purchase_history")
        
        # توصیه برند بر اساس ترجیحات
        if self.preferred_brands:
            recommendations["suggested_brands"] = self.preferred_brands[:3]
            recommendations["personalization_factors"].append("brand_preference")
        
        # توصیه بر اساس سبک رانندگی
        if self.riding_style:
            style_categories = {
                "city": ["کلاه کاسکت", "دستکش", "پوشاک موتورسواری"],
                "sport": ["کلاه کاسکت", "پروتکشن موتور سیکلت", "لاستیک موتور سیکلت"],
                "touring": ["باکس موتور سیکلت", "پوشاک موتورسواری", "لوازم جانبی"],
                "off-road": ["کلاه کاسکت", "پروتکشن موتور سیکلت", "لاستیک موتور سیکلت"]
            }
            
            if self.riding_style in style_categories:
                style_suggestions = style_categories[self.riding_style]
                recommendations["preferred_categories"].extend(style_suggestions)
                recommendations["personalization_factors"].append("riding_style")
        
        # حذف تکراری‌ها
        recommendations["preferred_categories"] = list(set(recommendations["preferred_categories"]))
        
        return recommendations

    async def _save_to_redis(self, rdb) -> None:
        """ذخیره پروفایل در Redis"""
        key = f"customer_profile:{self.session_id}"
        profile_data = self.dict()
        
        # تبدیل datetime به string برای JSON serialization
        profile_data["last_updated"] = self.last_updated.isoformat()
        
        await rdb.setex(key, 7 * 24 * 3600, json.dumps(profile_data, ensure_ascii=False))  # نگهداری 7 روز

    @classmethod
    async def load_from_redis(cls, session_id: str, rdb) -> Optional['CustomerProfile']:
        """بارگذاری پروفایل از Redis"""
        key = f"customer_profile:{session_id}"
        
        try:
            data = await rdb.get(key)
            if data:
                profile_data = json.loads(data)
                profile_data["last_updated"] = datetime.fromisoformat(profile_data["last_updated"])
                return cls(**profile_data)
        except Exception as e:
            print(f"Error loading customer profile: {e}")
        
        return None

    def get_context_summary(self) -> str:
        """خلاصه context برای استفاده در prompt"""
        context_parts = []
        
        if self.motorcycle_model:
            context_parts.append(f"موتور: {self.motorcycle_model}")
        
        if self.riding_style:
            context_parts.append(f"سبک رانندگی: {self.riding_style}")
        
        if self.budget_range:
            context_parts.append(f"بودجه: {self.budget_range}")
        
        if self.preferred_brands:
            context_parts.append(f"برندهای ترجیحی: {', '.join(self.preferred_brands[:2])}")
        
        if self.technical_expertise != "beginner":
            context_parts.append(f"سطح تخصص: {self.technical_expertise}")
        
        if self.customer_type != "new":
            context_parts.append(f"نوع مشتری: {self.customer_type}")
        
        return " | ".join(context_parts) if context_parts else "مشتری جدید"

    def should_show_technical_details(self) -> bool:
        """تعیین اینکه آیا باید جزئیات فنی نشان داده شود"""
        return self.technical_expertise in ["intermediate", "expert"]

    def get_price_filter_suggestion(self) -> Optional[Dict[str, float]]:
        """پیشنهاد فیلتر قیمت بر اساس پروفایل"""
        if not self.budget_range:
            return None
        
        budget_ranges = {
            "زیر ۵ میلیون": {"max": 5000000},
            "۵-۱۰ میلیون": {"min": 5000000, "max": 10000000},
            "۱۰-۲۰ میلیون": {"min": 10000000, "max": 20000000},
            "بیش از ۲۰ میلیون": {"min": 20000000}
        }
        
        return budget_ranges.get(self.budget_range, None)

