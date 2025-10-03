from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from enum import Enum

from app.memory.customer_profile import CustomerProfile
from app.intelligence.business_logic import QueryIntent

class ResponseStyle(Enum):
    """سبک‌های مختلف پاسخ"""
    EXPERT_CONSULTATION = "expert_consultation"      # مشاوره تخصصی
    DIRECT_SALES = "direct_sales"                   # فروش مستقیم
    EDUCATIONAL = "educational"                     # آموزشی
    COMPARATIVE_ANALYSIS = "comparative_analysis"   # تحلیل مقایسه‌ای
    PROBLEM_SOLVING = "problem_solving"             # حل مسئله

class ResponseFormatter:
    """فرمت‌کننده پاسخ حرفه‌ای برای تولید پاسخ‌های سطح ادمین"""
    
    def __init__(self):
        self.style_templates = self._initialize_style_templates()
        self.formatting_rules = self._initialize_formatting_rules()

    def format_expert_response(
        self,
        products: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        user_context: Dict[str, Any],
        reasoning_chain_result: Optional[Dict[str, Any]] = None,
        user_profile: Optional[CustomerProfile] = None
    ) -> str:
        """فرمت‌بندی پاسخ به سبک ادمین حرفه‌ای"""
        
        # تعیین سبک پاسخ
        response_style = self._determine_response_style(analysis, user_context)
        
        # انتخاب template مناسب
        template = self.style_templates.get(response_style, self.style_templates[ResponseStyle.EXPERT_CONSULTATION])
        
        # تولید بخش‌های مختلف پاسخ
        sections = {
            'greeting': self._generate_greeting(user_context, user_profile),
            'need_analysis': self._generate_need_analysis(analysis, user_context),
            'search_summary': self._generate_search_summary(products, analysis),
            'main_recommendations': self._format_main_recommendations(products, analysis, response_style),
            'comparative_analysis': self._generate_comparative_analysis(products, analysis),
            'complementary_products': self._format_complementary_products(analysis, user_context),
            'expert_insights': self._generate_expert_insights(products, analysis, user_profile),
            'guidance_and_tips': self._generate_guidance_section(analysis, user_context),
            'next_steps': self._generate_next_steps(analysis, user_context),
            'closing': self._generate_closing(response_style, user_context)
        }
        
        # ترکیب بخش‌ها بر اساس template
        response = self._assemble_response(template, sections, response_style)
        
        # اعمال قوانین فرمت‌بندی
        formatted_response = self._apply_formatting_rules(response, user_profile)
        
        return formatted_response

    def _determine_response_style(
        self, 
        analysis: Dict[str, Any], 
        user_context: Dict[str, Any]
    ) -> ResponseStyle:
        """تعیین سبک پاسخ مناسب"""
        
        # بر اساس intent اصلی
        intent_analysis = user_context.get('intent_analysis', {})
        primary_intent = intent_analysis.get('primary_intent', '')
        
        if primary_intent == QueryIntent.PURCHASE_READY.value:
            return ResponseStyle.DIRECT_SALES
        elif primary_intent == QueryIntent.COMPARISON_SEEKING.value:
            return ResponseStyle.COMPARATIVE_ANALYSIS
        elif primary_intent == QueryIntent.RESEARCH_PHASE.value:
            return ResponseStyle.EDUCATIONAL
        elif primary_intent == QueryIntent.TECHNICAL_SUPPORT.value:
            return ResponseStyle.PROBLEM_SOLVING
        else:
            return ResponseStyle.EXPERT_CONSULTATION

    def _generate_greeting(
        self, 
        user_context: Dict[str, Any], 
        user_profile: Optional[CustomerProfile]
    ) -> str:
        """تولید سلام و شناسایی نیاز"""
        
        greeting_parts = []
        
        # سلام شخصی‌سازی شده
        if user_profile and user_profile.customer_type == "returning":
            greeting_parts.append("سلام مجدد! 😊")
        elif user_profile and user_profile.customer_type == "loyal":
            greeting_parts.append("سلام دوست عزیز! 🙌")
        else:
            greeting_parts.append("سلام و وقت بخیر! 👋")
        
        # اشاره به تخصص
        greeting_parts.append("من **NeuraQueen** هستم، ادمین متخصص فروشگاه موتورسیکلت با بیش از 8 سال تجربه.")
        
        return " ".join(greeting_parts)

    def _generate_need_analysis(
        self, 
        analysis: Dict[str, Any], 
        user_context: Dict[str, Any]
    ) -> str:
        """تولید تحلیل نیاز"""
        
        need_analysis_parts = []
        need_analysis_parts.append("## 🎯 **تحلیل نیاز شما:**")
        
        # استخراج نیاز اصلی
        if analysis.get('need_analysis'):
            need_data = analysis['need_analysis']
            primary_need = need_data.get('primary_need', 'محصول موتورسیکلت')
            
            need_analysis_parts.append(f"بر اساس بررسی درخواست شما، به دنبال **{primary_need}** هستید.")
            
            # جزئیات اضافی
            details = []
            if need_data.get('budget_constraint'):
                budget_info = need_data['budget_constraint']
                details.append(f"بودجه: تا {budget_info.get('max', 0):,} تومان")
            
            if need_data.get('motorcycle_model'):
                details.append(f"موتور: {need_data['motorcycle_model']}")
            
            if need_data.get('urgency_level') == 'high':
                details.append("⚡ نیاز فوری")
            
            if details:
                need_analysis_parts.append(f"**مشخصات درخواست:** {' | '.join(details)}")
        
        return "\n".join(need_analysis_parts)

    def _generate_search_summary(
        self, 
        products: List[Dict[str, Any]], 
        analysis: Dict[str, Any]
    ) -> str:
        """تولید خلاصه نتایج جستجو"""
        
        if not products:
            return "## 📊 **نتایج جستجو:**\nمتأسفانه محصول مناسبی با معیارهای شما پیدا نکردم. 😕"
        
        summary_parts = []
        summary_parts.append("## 📊 **نتایج جستجو:**")
        
        # آمار کلی
        total_products = len(products)
        in_stock_count = len([p for p in products if 'موجود' in p.get('metadata', {}).get('stock', '')])
        
        summary_parts.append(f"✅ **{total_products} محصول مناسب** یافت شد ({in_stock_count} مورد موجود)")
        
        # کیفیت نتایج
        if analysis.get('search_quality'):
            quality = analysis['search_quality']
            if quality > 0.8:
                summary_parts.append("🎯 **کیفیت تطابق:** عالی - محصولات دقیقاً مطابق نیاز شما")
            elif quality > 0.6:
                summary_parts.append("✅ **کیفیت تطابق:** خوب - محصولات مناسب با نیاز شما")
            else:
                summary_parts.append("⚠️ **کیفیت تطابق:** متوسط - نزدیک‌ترین گزینه‌های موجود")
        
        return "\n".join(summary_parts)

    def _format_main_recommendations(
        self, 
        products: List[Dict[str, Any]], 
        analysis: Dict[str, Any],
        style: ResponseStyle
    ) -> str:
        """فرمت‌بندی توصیه‌های اصلی"""
        
        if not products:
            return ""
        
        rec_parts = []
        rec_parts.append("## 🏆 **توصیه‌های تخصصی من:**")
        
        # محصول اصلی (بهترین انتخاب)
        best_product = products[0]
        rec_parts.append(self._format_single_product(best_product, 1, "بهترین انتخاب", style))
        
        # گزینه‌های جایگزین
        if len(products) > 1:
            rec_parts.append("\n### 🔄 **گزینه‌های جایگزین:**")
            
            for i, product in enumerate(products[1:4], 2):  # حداکثر 3 جایگزین
                reason = self._determine_alternative_reason(product, best_product)
                rec_parts.append(self._format_single_product(product, i, reason, style))
        
        return "\n".join(rec_parts)

    def _format_single_product(
        self, 
        product: Dict[str, Any], 
        rank: int, 
        reason: str,
        style: ResponseStyle
    ) -> str:
        """فرمت‌بندی یک محصول"""
        
        metadata = product.get('metadata', {})
        
        product_parts = []
        
        # عنوان و رتبه
        name = metadata.get('name', 'نامشخص')
        brand = metadata.get('brand', 'نامشخص')
        product_parts.append(f"### {rank}. **{name}** ({brand}) - *{reason}*")
        
        # قیمت و ارزش
        price = metadata.get('price', 'نامشخص')
        price_numeric = metadata.get('price_numeric', 0)
        
        value_analysis = self._analyze_value(product)
        product_parts.append(f"💰 **قیمت:** {price} {value_analysis}")
        
        # ویژگی‌های کلیدی
        key_features = self._extract_key_features(metadata)
        if key_features:
            product_parts.append(f"⚡ **ویژگی‌های کلیدی:** {' | '.join(key_features)}")
        
        # موجودی و هشدارها
        stock_info = self._format_stock_info(metadata)
        if stock_info:
            product_parts.append(stock_info)
        
        # سازگاری
        compatibility_info = self._format_compatibility_info(metadata)
        if compatibility_info:
            product_parts.append(compatibility_info)
        
        # امتیاز کیفیت
        quality_score = self._calculate_display_quality_score(product)
        product_parts.append(f"📈 **امتیاز کیفیت:** {quality_score}/10")
        
        # لینک و تصویر
        link = metadata.get('link', '')
        image = metadata.get('image', '')
        
        if image:
            product_parts.append(f"🖼️ **[تصویر محصول]({image})**")
        
        if link:
            product_parts.append(f"🛒 **[مشاهده و خرید]({link})**")
        
        return "\n".join(product_parts)

    def _analyze_value(self, product: Dict[str, Any]) -> str:
        """تحلیل ارزش محصول"""
        metadata = product.get('metadata', {})
        price_numeric = metadata.get('price_numeric', 0)
        brand = metadata.get('brand', '').lower()
        
        # تحلیل نسبت قیمت به کیفیت
        if brand in ['yamaha', 'honda', 'suzuki'] and price_numeric < 15000000:
            return "*(ارزش عالی)*"
        elif price_numeric < 3000000:
            return "*(اقتصادی)*"
        elif price_numeric > 15000000:
            return "*(پریمیوم)*"
        else:
            return "*(متعادل)*"

    def _extract_key_features(self, metadata: Dict[str, Any]) -> List[str]:
        """استخراج ویژگی‌های کلیدی"""
        features = []
        
        # ویژگی‌های از metadata
        features_flat = metadata.get('features_flat', '').lower()
        
        # ویژگی‌های مهم
        important_features = {
            'اسپرت': '🏁 اسپرت',
            'شهری': '🏙️ شهری', 
            'کراسی': '🏔️ کراسی',
            'چهارفصل': '🌦️ چهارفصل',
            'پروتکشن': '🛡️ محافظت',
            'ضدآب': '💧 ضدآب',
            'تهویه': '💨 تهویه'
        }
        
        for keyword, display in important_features.items():
            if keyword in features_flat:
                features.append(display)
        
        # سایزهای موجود
        variations = metadata.get('variations', [])
        sizes = [v.get('size', '') for v in variations if v.get('size')]
        if sizes:
            features.append(f"📏 سایز: {', '.join(sizes[:3])}")
        
        return features[:4]  # حداکثر 4 ویژگی

    def _format_stock_info(self, metadata: Dict[str, Any]) -> str:
        """فرمت‌بندی اطلاعات موجودی"""
        stock = metadata.get('stock', '')
        
        if 'ناموجود' in stock:
            return "❌ **موجودی:** ناموجود"
        elif any(char.isdigit() and int(char) <= 2 for char in stock):
            return "⚠️ **موجودی:** محدود - سفارش فوری توصیه می‌شود!"
        elif any(char.isdigit() and int(char) <= 5 for char in stock):
            return "⏰ **موجودی:** کم - تعداد محدود در انبار"
        elif 'موجود' in stock:
            return "✅ **موجودی:** موجود در انبار"
        else:
            return ""

    def _format_compatibility_info(self, metadata: Dict[str, Any]) -> str:
        """فرمت‌بندی اطلاعات سازگاری"""
        category = metadata.get('category', '').lower()
        name = metadata.get('name', '').lower()
        
        if 'لاستیک' in category:
            # استخراج سایز لاستیک
            import re
            size_match = re.search(r'(\d{3})[/\\](\d{2})[/\\](\d{2})', name)
            if size_match:
                width, profile, rim = size_match.groups()
                return f"🔧 **سازگاری:** سایز {width}/{profile}/{rim} - بررسی سازگاری با موتور ضروری"
        
        elif 'کلاه' in category:
            return "🔧 **سازگاری:** مناسب همه موتورها - انتخاب سایز مناسب سر ضروری"
        
        elif 'پروتکشن' in category:
            if 'کلیک' in name:
                return "🔧 **سازگاری:** مخصوص موتورهای کلیک و طرح کلیک"
            elif 'آیروکس' in name:
                return "🔧 **سازگاری:** مخصوص موتورهای آیروکس"
        
        return ""

    def _calculate_display_quality_score(self, product: Dict[str, Any]) -> str:
        """محاسبه امتیاز کیفیت برای نمایش"""
        metadata = product.get('metadata', {})
        
        # عوامل امتیاز‌دهی
        score = 5.0  # امتیاز پایه
        
        # امتیاز برند
        brand = metadata.get('brand', '').lower()
        brand_scores = {
            'yamaha': 2.0, 'honda': 2.0, 'suzuki': 1.8, 'kawasaki': 1.8,
            'mt': 1.5, 'smk': 1.3, 'soman': 1.3, 'scoyco': 1.0,
            'fulmer': 0.8, 'beon': 0.8, 'qike': 0.5, 'redline': 0.3
        }
        score += brand_scores.get(brand, 0.0)
        
        # امتیاز قیمت (نسبت قیمت به کیفیت)
        price_numeric = metadata.get('price_numeric', 0)
        if 3000000 <= price_numeric <= 10000000:  # رنج قیمت مطلوب
            score += 1.0
        elif price_numeric < 2000000:  # خیلی ارزان
            score -= 0.5
        
        # امتیاز موجودی
        stock = metadata.get('stock', '')
        if 'موجود' in stock:
            score += 0.5
        elif 'ناموجود' in stock:
            score -= 1.0
        
        return f"{min(10.0, max(1.0, score)):.1f}"

    def _determine_alternative_reason(
        self, 
        alternative: Dict[str, Any], 
        best_choice: Dict[str, Any]
    ) -> str:
        """تعیین دلیل پیشنهاد جایگزین"""
        alt_metadata = alternative.get('metadata', {})
        best_metadata = best_choice.get('metadata', {})
        
        alt_price = alt_metadata.get('price_numeric', 0)
        best_price = best_metadata.get('price_numeric', 0)
        
        if alt_price < best_price * 0.8:
            return "گزینه اقتصادی"
        elif alt_price > best_price * 1.3:
            return "کیفیت پریمیوم"
        elif alt_metadata.get('brand') != best_metadata.get('brand'):
            return "برند متفاوت"
        else:
            return "ویژگی‌های متفاوت"

    def _generate_comparative_analysis(
        self, 
        products: List[Dict[str, Any]], 
        analysis: Dict[str, Any]
    ) -> str:
        """تولید تحلیل مقایسه‌ای"""
        
        if len(products) < 2:
            return ""
        
        comp_parts = []
        comp_parts.append("## 📊 **تحلیل مقایسه‌ای:**")
        
        # مقایسه قیمت
        prices = [p.get('metadata', {}).get('price_numeric', 0) for p in products[:3]]
        min_price = min(p for p in prices if p > 0)
        max_price = max(prices)
        
        comp_parts.append(f"💰 **محدوده قیمت:** {min_price:,} تا {max_price:,} تومان")
        
        # مقایسه برندها
        brands = list(set([p.get('metadata', {}).get('brand', 'نامشخص') for p in products[:3]]))
        comp_parts.append(f"🏷️ **برندهای موجود:** {', '.join(brands)}")
        
        # نکات مقایسه‌ای
        comparison_insights = []
        
        # بهترین ارزش
        best_value = min(products[:3], key=lambda x: x.get('metadata', {}).get('price_numeric', float('inf')))
        comparison_insights.append(f"💡 **بهترین قیمت:** {best_value.get('metadata', {}).get('name', 'نامشخص')}")
        
        # بهترین کیفیت
        premium_brands = ['yamaha', 'honda', 'suzuki', 'kawasaki', 'mt']
        quality_products = [p for p in products[:3] if p.get('metadata', {}).get('brand', '').lower() in premium_brands]
        if quality_products:
            best_quality = quality_products[0]
            comparison_insights.append(f"🏆 **بهترین کیفیت:** {best_quality.get('metadata', {}).get('name', 'نامشخص')}")
        
        if comparison_insights:
            comp_parts.extend(comparison_insights)
        
        return "\n".join(comp_parts)

    def _format_complementary_products(
        self, 
        analysis: Dict[str, Any], 
        user_context: Dict[str, Any]
    ) -> str:
        """فرمت‌بندی محصولات مکمل"""
        
        complementary = analysis.get('complementary_products', {})
        
        if not complementary or not complementary.get('complementary_products'):
            return ""
        
        comp_parts = []
        comp_parts.append("## 🔗 **محصولات مکمل پیشنهادی:**")
        
        # محصولات اولویت بالا
        priority_items = complementary.get('priority_items', [])
        if priority_items:
            comp_parts.append("### ⚡ **ضروری:**")
            for item in priority_items[:2]:
                name = item.get('product_name', 'نامشخص')
                price = item.get('price', 'نامشخص')
                reason = item.get('reason', 'محصول مکمل')
                comp_parts.append(f"• **{name}** ({price}) - {reason}")
        
        # محصولات اختیاری
        optional_items = complementary.get('optional_items', [])
        if optional_items:
            comp_parts.append("### 💡 **پیشنهادی:**")
            for item in optional_items[:2]:
                name = item.get('product_name', 'نامشخص')
                price = item.get('price', 'نامشخص')
                reason = item.get('reason', 'محصول مکمل')
                comp_parts.append(f"• **{name}** ({price}) - {reason}")
        
        # ارزش کل
        total_value = complementary.get('total_value', 0)
        if total_value > 0:
            comp_parts.append(f"\n💰 **ارزش کل محصولات مکمل:** {total_value:,} تومان")
        
        return "\n".join(comp_parts)

    def _generate_expert_insights(
        self, 
        products: List[Dict[str, Any]], 
        analysis: Dict[str, Any],
        user_profile: Optional[CustomerProfile]
    ) -> str:
        """تولید بینش‌های تخصصی"""
        
        insights_parts = []
        insights_parts.append("## 💡 **بینش‌های تخصصی:**")
        
        insights = []
        
        # بینش بر اساس انتخاب محصولات
        if products:
            best_product = products[0]
            category = best_product.get('metadata', {}).get('category', '')
            
            if 'کلاه کاسکت' in category:
                insights.append("🛡️ **نکته ایمنی:** حتماً استاندارد DOT یا ECE را بررسی کنید")
                insights.append("📏 **نکته سایز:** کلاه باید محکم روی سر باشد اما فشار نیاورد")
            
            elif 'لاستیک' in category:
                insights.append("⚠️ **نکته مهم:** سایز لاستیک باید دقیقاً مطابق مشخصات موتور باشد")
                insights.append("🔧 **نکته نصب:** نصب توسط متخصص و بالانس چرخ ضروری است")
            
            elif 'دستکش' in category:
                insights.append("✋ **نکته سایز:** دستکش باید انگشتان را کاملاً بپوشاند")
                insights.append("🧤 **نکته کیفیت:** مفاصل انگشتان باید انعطاف‌پذیر باشند")
        
        # بینش بر اساس پروفایل کاربر
        if user_profile:
            if user_profile.technical_expertise == 'beginner':
                insights.append("📚 **توصیه:** مطالعه دفترچه راهنما قبل از استفاده ضروری است")
            
            if user_profile.price_sensitivity == 'high':
                insights.append("💰 **نکته اقتصادی:** در نظر گیری هزینه‌های جانبی مثل نصب و نگهداری")
        
        # بینش‌های عمومی
        insights.append("🔄 **نکته مهم:** در صورت عدم رضایت، امکان تعویض در 7 روز اول وجود دارد")
        insights.append("📞 **پشتیبانی:** برای مشاوره تخصصی بیشتر، با ما تماس بگیرید")
        
        if insights:
            insights_parts.extend(insights[:4])  # حداکثر 4 بینش
        
        return "\n".join(insights_parts)

    def _generate_guidance_section(
        self, 
        analysis: Dict[str, Any], 
        user_context: Dict[str, Any]
    ) -> str:
        """تولید بخش راهنمایی"""
        
        guidance = analysis.get('guidance', {})
        
        if not guidance:
            return ""
        
        guidance_parts = []
        guidance_parts.append("## 🎯 **راهنمایی تخصصی:**")
        
        # نکات نصب
        installation_tips = guidance.get('installation_tips', [])
        if installation_tips:
            guidance_parts.append("### 🔧 **نکات نصب:**")
            for tip in installation_tips[:3]:
                guidance_parts.append(f"• {tip}")
        
        # نکات نگهداری
        maintenance_advice = guidance.get('maintenance_advice', [])
        if maintenance_advice:
            guidance_parts.append("### 🛠️ **نکات نگهداری:**")
            for advice in maintenance_advice[:3]:
                guidance_parts.append(f"• {advice}")
        
        # هشدارهای ایمنی
        safety_warnings = guidance.get('safety_warnings', [])
        if safety_warnings:
            guidance_parts.append("### ⚠️ **نکات ایمنی:**")
            for warning in safety_warnings[:3]:
                guidance_parts.append(f"• {warning}")
        
        return "\n".join(guidance_parts)

    def _generate_next_steps(
        self, 
        analysis: Dict[str, Any], 
        user_context: Dict[str, Any]
    ) -> str:
        """تولید قدم‌های بعدی"""
        
        next_steps_parts = []
        next_steps_parts.append("## 🚀 **قدم‌های بعدی:**")
        
        # قدم‌ها بر اساس intent
        intent_analysis = user_context.get('intent_analysis', {})
        primary_intent = intent_analysis.get('primary_intent', '')
        
        if primary_intent == QueryIntent.PURCHASE_READY.value:
            next_steps_parts.extend([
                "1. 🛒 **انتخاب سایز مناسب** (در صورت نیاز)",
                "2. 📞 **تماس برای تأیید موجودی**",
                "3. 💳 **ثبت سفارش و پرداخت**",
                "4. 🚚 **هماهنگی زمان ارسال**"
            ])
        else:
            next_steps_parts.extend([
                "1. 📋 **مقایسه گزینه‌های پیشنهادی**",
                "2. 💬 **مشورت با متخصص** (در صورت نیاز)",
                "3. 🔍 **بررسی جزئیات بیشتر محصولات**",
                "4. ✅ **تصمیم نهایی و خرید**"
            ])
        
        # اولویت‌بندی بر اساس فوریت
        urgency = user_context.get('urgency_level', 'low')
        if urgency == 'high':
            next_steps_parts.append("\n⚡ **توجه:** با توجه به نیاز فوری شما، توصیه می‌کنم سریعاً اقدام کنید.")
        
        return "\n".join(next_steps_parts)

    def _generate_closing(
        self, 
        style: ResponseStyle, 
        user_context: Dict[str, Any]
    ) -> str:
        """تولید پایان پاسخ"""
        
        closing_parts = []
        
        # پایان متناسب با سبک
        if style == ResponseStyle.DIRECT_SALES:
            closing_parts.append("بر اساس تجربه 8 ساله‌ام، این انتخاب‌ها بهترین گزینه‌ها برای شما هستند.")
        elif style == ResponseStyle.EDUCATIONAL:
            closing_parts.append("امیدوارم این اطلاعات برای تصمیم‌گیری بهتر شما مفید باشد.")
        else:
            closing_parts.append("بر اساس تحلیل تخصصی، این توصیه‌ها بهترین انتخاب برای نیاز شما هستند.")
        
        # سوال نهایی
        closing_parts.append("\n**سوال دیگه‌ای داری یا می‌خوای راجع به موضوع خاصی بیشتر صحبت کنیم؟** 🤝")
        
        return "\n".join(closing_parts)

    def _initialize_style_templates(self) -> Dict[ResponseStyle, Dict[str, bool]]:
        """مقداردهی template های مختلف"""
        return {
            ResponseStyle.EXPERT_CONSULTATION: {
                'greeting': True,
                'need_analysis': True,
                'search_summary': True,
                'main_recommendations': True,
                'comparative_analysis': True,
                'complementary_products': True,
                'expert_insights': True,
                'guidance_and_tips': True,
                'next_steps': True,
                'closing': True
            },
            ResponseStyle.DIRECT_SALES: {
                'greeting': True,
                'need_analysis': False,
                'search_summary': True,
                'main_recommendations': True,
                'comparative_analysis': False,
                'complementary_products': True,
                'expert_insights': False,
                'guidance_and_tips': False,
                'next_steps': True,
                'closing': True
            },
            ResponseStyle.EDUCATIONAL: {
                'greeting': True,
                'need_analysis': True,
                'search_summary': True,
                'main_recommendations': True,
                'comparative_analysis': True,
                'complementary_products': False,
                'expert_insights': True,
                'guidance_and_tips': True,
                'next_steps': True,
                'closing': True
            },
            ResponseStyle.COMPARATIVE_ANALYSIS: {
                'greeting': True,
                'need_analysis': False,
                'search_summary': True,
                'main_recommendations': True,
                'comparative_analysis': True,
                'complementary_products': False,
                'expert_insights': True,
                'guidance_and_tips': False,
                'next_steps': True,
                'closing': True
            },
            ResponseStyle.PROBLEM_SOLVING: {
                'greeting': True,
                'need_analysis': True,
                'search_summary': False,
                'main_recommendations': True,
                'comparative_analysis': False,
                'complementary_products': False,
                'expert_insights': True,
                'guidance_and_tips': True,
                'next_steps': True,
                'closing': True
            }
        }

    def _initialize_formatting_rules(self) -> Dict[str, Any]:
        """مقداردهی قوانین فرمت‌بندی"""
        return {
            'max_product_display': 5,
            'max_alternatives': 3,
            'max_complementary': 4,
            'max_insights': 4,
            'use_emojis': True,
            'use_markdown': True,
            'include_links': True,
            'personalization_level': 'high'
        }

    def _assemble_response(
        self, 
        template: Dict[str, bool], 
        sections: Dict[str, str],
        style: ResponseStyle
    ) -> str:
        """ترکیب بخش‌های پاسخ بر اساس template"""
        
        response_parts = []
        
        # ترتیب اجرای بخش‌ها
        section_order = [
            'greeting',
            'need_analysis', 
            'search_summary',
            'main_recommendations',
            'comparative_analysis',
            'complementary_products',
            'expert_insights',
            'guidance_and_tips',
            'next_steps',
            'closing'
        ]
        
        for section_name in section_order:
            if template.get(section_name, False) and sections.get(section_name):
                response_parts.append(sections[section_name])
        
        return "\n\n".join(response_parts)

    def _apply_formatting_rules(
        self, 
        response: str, 
        user_profile: Optional[CustomerProfile]
    ) -> str:
        """اعمال قوانین فرمت‌بندی"""
        
        formatted_response = response
        
        # شخصی‌سازی بر اساس سطح تخصص
        if user_profile and user_profile.technical_expertise == 'beginner':
            # ساده‌سازی زبان فنی
            formatted_response = formatted_response.replace('compatibility', 'سازگاری')
            formatted_response = formatted_response.replace('specification', 'مشخصات')
        
        # اضافه کردن فاصله‌های مناسب
        formatted_response = formatted_response.replace('\n\n\n', '\n\n')
        
        # تأکید بر نکات مهم
        formatted_response = formatted_response.replace('⚠️ **توجه:**', '\n⚠️ **توجه مهم:**')
        
        return formatted_response

