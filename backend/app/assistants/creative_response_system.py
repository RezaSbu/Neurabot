"""
سیستم تولید پاسخ‌های خلاقانه و پیشنهادی
"""
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ResponseStyle(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EXPERT = "expert"
    ENCOURAGING = "encouraging"
    INFORMATIVE = "informative"

class SuggestionType(Enum):
    ALTERNATIVE = "alternative"
    UPGRADE = "upgrade"
    BUDGET_FRIENDLY = "budget_friendly"
    PREMIUM = "premium"
    COMPLEMENTARY = "complementary"

@dataclass
class CreativeSuggestion:
    type: SuggestionType
    title: str
    description: str
    reasoning: str
    emoji: str
    confidence: float

@dataclass
class ResponseEnhancement:
    style: ResponseStyle
    suggestions: List[CreativeSuggestion]
    insights: List[str]
    tips: List[str]
    warnings: List[str]

class CreativeResponseSystem:
    def __init__(self):
        self.emoji_map = {
            "کلاه کاسکت": "🪖",
            "پوشاک موتورسواری": "👕",
            "دستکش": "🧤",
            "لاستیک": "🛞",
            "پروتکشن": "🛡️",
            "باکس": "📦",
            "لوازم جانبی": "🔧",
            "روغن": "🛢️"
        }
        
        self.creative_templates = {
            "alternative": [
                "اگر {original} را دوست نداشتید، {alternative} گزینه عالی دیگری است که {reasoning}",
                "یک انتخاب جالب دیگر {alternative} است که {reasoning}",
                "برای تنوع بیشتر، {alternative} را هم در نظر بگیرید که {reasoning}"
            ],
            "upgrade": [
                "اگر کمی بیشتر سرمایه‌گذاری کنید، {upgrade} را پیشنهاد می‌کنم که {reasoning}",
                "برای تجربه بهتر، {upgrade} انتخاب بهتری است چون {reasoning}",
                "اگر کیفیت اولویت شماست، {upgrade} ارزش بیشتری دارد"
            ],
            "budget_friendly": [
                "برای بودجه محدود، {budget_option} گزینه اقتصادی‌تری است که {reasoning}",
                "اگر دنبال قیمت مناسب هستید، {budget_option} را ببینید",
                "با همین بودجه، {budget_option} عملکرد خوبی ارائه می‌دهد"
            ],
            "complementary": [
                "همراه {main_product}، {complementary} را هم پیشنهاد می‌کنم چون {reasoning}",
                "برای تکمیل تجهیزات، {complementary} ضروری است",
                "{complementary} مکمل خوبی برای {main_product} محسوب می‌شود"
            ]
        }
        
        self.insight_templates = [
            "💡 نکته تخصصی: {insight}",
            "🔍 از نظر کارشناسی: {insight}",
            "⭐ تجربه کاربری: {insight}",
            "🎯 توصیه حرفه‌ای: {insight}",
            "📊 تحلیل بازار: {insight}"
        ]
        
        self.tip_templates = [
            "💡 راهنمای خرید: {tip}",
            "🔧 نکته نگهداری: {tip}",
            "⚡ نکته ایمنی: {tip}",
            "🎨 نکته استایل: {tip}",
            "💰 نکته اقتصادی: {tip}"
        ]

    async def enhance_response(self, 
                             products: List[Dict], 
                             query_context: Dict, 
                             user_intent: str,
                             response_style: ResponseStyle = ResponseStyle.FRIENDLY) -> ResponseEnhancement:
        """
        بهبود پاسخ با اضافه کردن عناصر خلاقانه
        """
        suggestions = await self._generate_creative_suggestions(products, query_context, user_intent)
        insights = await self._generate_insights(products, query_context)
        tips = await self._generate_tips(products, query_context, user_intent)
        warnings = await self._generate_warnings(products, query_context)
        
        return ResponseEnhancement(
            style=response_style,
            suggestions=suggestions,
            insights=insights,
            tips=tips,
            warnings=warnings
        )

    async def _generate_creative_suggestions(self, products: List[Dict], query_context: Dict, user_intent: str) -> List[CreativeSuggestion]:
        """
        تولید پیشنهادات خلاقانه
        """
        suggestions = []
        
        # پیشنهادات جایگزین
        if len(products) > 0:
            main_product = products[0]
            category = main_product.get('category', 'نامشخص')
            
            # پیشنهاد upgrade
            upgrade_suggestion = self._suggest_upgrade(main_product, category)
            if upgrade_suggestion:
                suggestions.append(upgrade_suggestion)
            
            # پیشنهاد budget-friendly
            budget_suggestion = self._suggest_budget_friendly(main_product, category)
            if budget_suggestion:
                suggestions.append(budget_suggestion)
            
            # پیشنهادات مکمل
            complementary_suggestions = self._suggest_complementary(main_product, category)
            suggestions.extend(complementary_suggestions)
        
        return suggestions[:4]  # حداکثر 4 پیشنهاد

    def _suggest_upgrade(self, main_product: Dict, category: str) -> Optional[CreativeSuggestion]:
        """
        پیشنهاد محصولات با کیفیت بالاتر
        """
        price = main_product.get('price_numeric', 0)
        brand = main_product.get('brand', '').lower()
        
        upgrade_reasons = {
            "کلاه کاسکت": {
                "reasoning": "امنیت و راحتی بیشتری در طولانی‌مدت ارائه می‌دهد",
                "price_threshold": 3000000
            },
            "پوشاک موتورسواری": {
                "reasoning": "دوام و محافظت بهتری در برابر شرایط مختلف آب و هوایی دارد",
                "price_threshold": 2000000
            },
            "لاستیک موتور سیکلت": {
                "reasoning": "عملکرد بهتر در جاده‌های مختلف و طول عمر بیشتر",
                "price_threshold": 1500000
            }
        }
        
        if category in upgrade_reasons and price < upgrade_reasons[category]["price_threshold"]:
            return CreativeSuggestion(
                type=SuggestionType.UPGRADE,
                title="گزینه با کیفیت بالاتر",
                description=f"محصولات با کیفیت بهتر در همین دسته‌بندی",
                reasoning=upgrade_reasons[category]["reasoning"],
                emoji="⬆️",
                confidence=0.8
            )
        
        return None

    def _suggest_budget_friendly(self, main_product: Dict, category: str) -> Optional[CreativeSuggestion]:
        """
        پیشنهاد محصولات اقتصادی‌تر
        """
        price = main_product.get('price_numeric', 0)
        
        budget_reasons = {
            "کلاه کاسکت": "همچنان استانداردهای ایمنی را رعایت می‌کند",
            "پوشاک موتورسواری": "محافظت اساسی را با قیمت مناسب ارائه می‌دهد",
            "لاستیک موتور سیکلت": "عملکرد قابل قبولی برای استفاده روزمره دارد"
        }
        
        if category in budget_reasons and price > 2000000:
            return CreativeSuggestion(
                type=SuggestionType.BUDGET_FRIENDLY,
                title="گزینه اقتصادی",
                description=f"محصولات با قیمت مناسب‌تر در همین دسته‌بندی",
                reasoning=budget_reasons[category],
                emoji="💰",
                confidence=0.7
            )
        
        return None

    def _suggest_complementary(self, main_product: Dict, category: str) -> List[CreativeSuggestion]:
        """
        پیشنهاد محصولات مکمل
        """
        suggestions = []
        
        complementary_map = {
            "کلاه کاسکت": [
                {"item": "لوازم کلاه کاسکت", "reasoning": "برای نگهداری و تمیز کردن کلاه ضروری است"},
                {"item": "دستکش", "reasoning": "تکمیل تجهیزات ایمنی برای موتورسوار"}
            ],
            "دستکش": [
                {"item": "کاپشن", "reasoning": "تکمیل پوشاک موتورسواری"},
                {"item": "چکمه", "reasoning": "محافظت کامل از دست تا پا"}
            ],
            "لاستیک موتور سیکلت": [
                {"item": "روغن موتور", "reasoning": "نگهداری منظم موتور ضروری است"},
                {"item": "روغن ترمز", "reasoning": "سیستم ترمز نیاز به نگهداری دارد"}
            ]
        }
        
        if category in complementary_map:
            for item in complementary_map[category]:
                suggestions.append(CreativeSuggestion(
                    type=SuggestionType.COMPLEMENTARY,
                    title=f"مکمل: {item['item']}",
                    description=f"محصولات مرتبط برای تکمیل تجهیزات",
                    reasoning=item['reasoning'],
                    emoji="🔗",
                    confidence=0.9
                ))
        
        return suggestions

    async def _generate_insights(self, products: List[Dict], query_context: Dict) -> List[str]:
        """
        تولید بینش‌های تخصصی
        """
        insights = []
        
        if not products:
            return insights
        
        # بینش بر اساس دسته‌بندی
        category = products[0].get('category', 'نامشخص')
        category_insights = {
            "کلاه کاسکت": [
                "کلاه‌های کربن فیبر سبک‌تر و مقاوم‌تر هستند",
                "کلاه‌های با سیستم تهویه بهتر برای تابستان مناسب‌ترند",
                "برندهای معتبر استانداردهای ایمنی بالاتری دارند"
            ],
            "پوشاک موتورسواری": [
                "پوشاک با لایه‌های متعدد انعطاف‌پذیری بیشتری در فصول مختلف دارد",
                "درزهای آب‌بند برای باران ضروری هستند",
                "پوشاک با رنگ‌های روشن دید بهتری در شب ارائه می‌دهند"
            ],
            "لاستیک موتور سیکلت": [
                "لاستیک‌های جدیدتر تکنولوژی‌های پیشرفته‌تری دارند",
                "پهنا و ارتفاع لاستیک بر عملکرد تأثیر مستقیم دارد",
                "لاستیک‌های اسپرت برای استفاده شهری مناسب‌ترند"
            ]
        }
        
        if category in category_insights:
            selected_insights = random.sample(category_insights[category], 
                                            min(2, len(category_insights[category])))
            for insight in selected_insights:
                template = random.choice(self.insight_templates)
                insights.append(template.format(insight=insight))
        
        # بینش بر اساس قیمت
        prices = [p.get('price_numeric', 0) for p in products if p.get('price_numeric', 0) > 0]
        if prices:
            avg_price = sum(prices) / len(prices)
            if avg_price > 5000000:
                insights.append("💎 محصولات پریمیوم: این رنج قیمت معمولاً کیفیت و دوام بالاتری دارد")
            elif avg_price < 2000000:
                insights.append("💰 محصولات اقتصادی: گزینه‌های مناسب برای بودجه محدود")
        
        return insights

    async def _generate_tips(self, products: List[Dict], query_context: Dict, user_intent: str) -> List[str]:
        """
        تولید نکات مفید
        """
        tips = []
        
        if not products:
            return tips
        
        category = products[0].get('category', 'نامشخص')
        
        # نکات بر اساس دسته‌بندی
        category_tips = {
            "کلاه کاسکت": [
                "حتماً سایز کلاه را دقیق اندازه‌گیری کنید",
                "کلاه نباید خیلی تنگ یا شل باشد",
                "هر 5 سال یکبار کلاه را تعویض کنید"
            ],
            "پوشاک موتورسواری": [
                "پوشاک را یک سایز بزرگ‌تر انتخاب کنید تا راحت‌تر باشد",
                "قبل از خرید در مورد آب‌بندی سؤال کنید",
                "پوشاک با زیپ‌های محکم‌تر دوام بیشتری دارد"
            ],
            "لاستیک موتور سیکلت": [
                "فشار باد لاستیک را مرتب چک کنید",
                "لاستیک‌های جلو و عقب ممکن است متفاوت باشند",
                "آج لاستیک را برای ساییدگی بررسی کنید"
            ]
        }
        
        if category in category_tips:
            selected_tips = random.sample(category_tips[category], 
                                        min(2, len(category_tips[category])))
            for tip in selected_tips:
                template = random.choice(self.tip_templates)
                tips.append(template.format(tip=tip))
        
        # نکات بر اساس intent
        if user_intent == "search_product":
            tips.append("🔍 نکته جستجو: برای نتایج بهتر، ویژگی‌های خاص مورد نظرتان را ذکر کنید")
        elif user_intent == "compare_products":
            tips.append("⚖️ نکته مقایسه: محصولات را بر اساس نیاز و بودجه خود مقایسه کنید")
        
        return tips

    async def _generate_warnings(self, products: List[Dict], query_context: Dict) -> List[str]:
        """
        تولید هشدارها و نکات احتیاطی
        """
        warnings = []
        
        if not products:
            return warnings
        
        # هشدار موجودی کم
        low_stock_products = [p for p in products 
                            if isinstance(p.get('stock'), str) and 
                            any(word in p['stock'].lower() for word in ['کم', 'اندک', 'محدود'])]
        
        if low_stock_products:
            warnings.append("⚠️ هشدار موجودی: برخی محصولات موجودی محدودی دارند")
        
        # هشدار قیمت
        expensive_products = [p for p in products 
                            if p.get('price_numeric', 0) > 10000000]
        
        if expensive_products:
            warnings.append("💸 هشدار قیمت: محصولات پریمیوم معمولاً نیاز به بودجه بالاتری دارند")
        
        # هشدار بر اساس فصل
        season = query_context.get('season')
        if season == "زمستان":
            warnings.append("❄️ نکته زمستانی: برای زمستان به محصولات ضد آب و گرم توجه کنید")
        elif season == "تابستان":
            warnings.append("☀️ نکته تابستانی: برای تابستان به تهویه و تنفس محصولات توجه کنید")
        
        return warnings

    def format_creative_response(self, enhancement: ResponseEnhancement, base_response: str) -> str:
        """
        فرمت کردن پاسخ نهایی با عناصر خلاقانه
        """
        response_parts = [base_response]
        
        # اضافه کردن پیشنهادات
        if enhancement.suggestions:
            response_parts.append("\n🎯 پیشنهادات خلاقانه:")
            for i, suggestion in enumerate(enhancement.suggestions, 1):
                response_parts.append(f"{i}. {suggestion.emoji} {suggestion.title}: {suggestion.description}")
                response_parts.append(f"   💭 {suggestion.reasoning}")
        
        # اضافه کردن بینش‌ها
        if enhancement.insights:
            response_parts.append("\n🔍 بینش‌های تخصصی:")
            for insight in enhancement.insights:
                response_parts.append(f"• {insight}")
        
        # اضافه کردن نکات
        if enhancement.tips:
            response_parts.append("\n💡 نکات مفید:")
            for tip in enhancement.tips:
                response_parts.append(f"• {tip}")
        
        # اضافه کردن هشدارها
        if enhancement.warnings:
            response_parts.append("\n⚠️ نکات مهم:")
            for warning in enhancement.warnings:
                response_parts.append(f"• {warning}")
        
        return "\n".join(response_parts)

    def get_emoji_for_category(self, category: str) -> str:
        """
        دریافت ایموجی مناسب برای دسته‌بندی
        """
        return self.emoji_map.get(category, "🛍️")

    def generate_encouraging_closing(self, user_intent: str, found_products: int) -> str:
        """
        تولید پایان‌بندی تشویق‌کننده
        """
        if found_products == 0:
            return "😊 نگران نباشید! با اطلاعات بیشتر می‌توانم بهتر کمک کنم. سوالات بیشتری بپرسید! 🤔"
        elif found_products < 3:
            return "😊 امیدوارم این موارد مفید باشند! اگر سوال بیشتری دارید، حتماً بپرسید! 💪"
        else:
            return "😊 انتخاب‌های خوبی پیش روی شماست! اگر نیاز به راهنمایی بیشتر دارید، در خدمتم! 🚀"
