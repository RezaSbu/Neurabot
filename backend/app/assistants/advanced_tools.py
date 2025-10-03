from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from app.db import search_hybrid_db, get_all_vectors
from app.openai import get_embedding
from app.config import settings
import numpy as np
from numpy.linalg import norm
import re
import json
import asyncio
from datetime import datetime, timedelta

class ProductComparisonTool(BaseModel):
    """مقایسه تخصصی 2-5 محصول با معیارهای فنی دقیق"""
    product_ids: List[str] = Field(..., description="شناسه محصولات برای مقایسه")
    comparison_criteria: List[str] = Field(
        default=["price", "quality", "compatibility", "features"], 
        description="معیارهای مقایسه"
    )
    user_priorities: Optional[List[str]] = Field(None, description="اولویت‌های کاربر")

    async def __call__(self, rdb):
        if len(self.product_ids) < 2:
            return json.dumps({
                "error": "حداقل 2 محصول برای مقایسه نیاز است",
                "products_count": len(self.product_ids)
            }, ensure_ascii=False)

        # دریافت اطلاعات محصولات
        products = []
        for product_id in self.product_ids[:5]:  # حداکثر 5 محصول
            # جستجو بر اساس product_id
            query_vector = await get_embedding(product_id)
            results = await search_hybrid_db(rdb, query_vector, product_id, top_k=5)
            
            for result in results:
                metadata = result.get('metadata', {})
                if metadata.get('product_id') == product_id:
                    products.append(metadata)
                    break

        if len(products) < 2:
            return json.dumps({
                "error": "تعداد کافی محصول برای مقایسه پیدا نشد",
                "found_products": len(products)
            }, ensure_ascii=False)

        # تحلیل مقایسه‌ای
        comparison_result = {
            "comparison_type": "expert_analysis",
            "products_count": len(products),
            "criteria": self.comparison_criteria,
            "products": [],
            "summary": {
                "best_value": None,
                "best_quality": None,
                "most_affordable": None,
                "recommendations": []
            }
        }

        best_value_score = 0
        best_quality_score = 0
        lowest_price = float('inf')

        for i, product in enumerate(products):
            price_numeric = product.get('price_numeric', 0)
            brand = product.get('brand', 'نامشخص')
            
            # محاسبه امتیاز کیفیت (بر اساس برند و قیمت)
            quality_score = self._calculate_quality_score(brand, price_numeric)
            
            # محاسبه امتیاز ارزش (نسبت کیفیت به قیمت)
            value_score = quality_score / max(price_numeric, 1) * 1000000 if price_numeric > 0 else 0

            product_analysis = {
                "rank": i + 1,
                "name": product.get('name', 'نامشخص'),
                "brand": brand,
                "price": product.get('price', 'نامشخص'),
                "price_numeric": price_numeric,
                "quality_score": round(quality_score, 1),
                "value_score": round(value_score, 1),
                "features": product.get('features_flat', ''),
                "sizes": [v.get('size', '') for v in product.get('variations', []) if v.get('size')],
                "stock": product.get('stock', 'نامشخص'),
                "image": product.get('image', ''),
                "link": product.get('link', ''),
                "pros": self._extract_pros(product),
                "cons": self._extract_cons(product),
                "compatibility": self._assess_compatibility(product),
                "recommendation_reason": ""
            }

            # تعیین بهترین‌ها
            if value_score > best_value_score:
                best_value_score = value_score
                comparison_result["summary"]["best_value"] = product_analysis["name"]

            if quality_score > best_quality_score:
                best_quality_score = quality_score
                comparison_result["summary"]["best_quality"] = product_analysis["name"]

            if price_numeric < lowest_price and price_numeric > 0:
                lowest_price = price_numeric
                comparison_result["summary"]["most_affordable"] = product_analysis["name"]

            comparison_result["products"].append(product_analysis)

        # تولید توصیه‌های نهایی
        comparison_result["summary"]["recommendations"] = self._generate_recommendations(
            comparison_result["products"], self.user_priorities
        )

        return json.dumps(comparison_result, ensure_ascii=False)

    def _calculate_quality_score(self, brand: str, price: float) -> float:
        """محاسبه امتیاز کیفیت بر اساس برند و قیمت"""
        brand_scores = {
            'yamaha': 9.5, 'honda': 9.5, 'suzuki': 9.0, 'kawasaki': 9.0,
            'mt': 8.5, 'smk': 8.0, 'soman': 8.0, 'scoyco': 7.5,
            'fulmer': 7.0, 'beon': 7.0, 'qike': 6.5, 'redline': 6.0,
            'ردلاین': 6.0, 'ایران یاسا': 5.5, 'نامشخص': 5.0
        }
        
        brand_lower = brand.lower()
        brand_score = brand_scores.get(brand_lower, 5.0)
        
        # تعدیل بر اساس قیمت (محصولات گران‌تر معمولاً کیفیت بهتری دارند)
        if price > 10000000:  # بالای 10 میلیون
            price_bonus = 1.0
        elif price > 5000000:  # بالای 5 میلیون
            price_bonus = 0.5
        else:
            price_bonus = 0.0
            
        return min(10.0, brand_score + price_bonus)

    def _extract_pros(self, product: Dict) -> List[str]:
        """استخراج مزایای محصول"""
        pros = []
        features = product.get('features_flat', '').lower()
        brand = product.get('brand', '').lower()
        price = product.get('price_numeric', 0)
        
        if 'پروتکشن' in features or 'محافظ' in features:
            pros.append('دارای سیستم محافظت')
        if 'چهارفصل' in features:
            pros.append('مناسب تمام فصول')
        if 'اسپرت' in features:
            pros.append('طراحی اسپرت')
        if brand in ['yamaha', 'honda', 'suzuki', 'mt', 'smk']:
            pros.append('برند معتبر')
        if price < 3000000:
            pros.append('قیمت مناسب')
        
        return pros[:3]  # حداکثر 3 مزیت

    def _extract_cons(self, product: Dict) -> List[str]:
        """استخراج معایب محصول"""
        cons = []
        brand = product.get('brand', '').lower()
        price = product.get('price_numeric', 0)
        stock = product.get('stock', '')
        
        if brand == 'نامشخص':
            cons.append('برند نامشخص')
        if price > 15000000:
            cons.append('قیمت بالا')
        if 'کم' in stock or ('عدد' in stock and any(char.isdigit() and int(char) < 3 for char in stock)):
            cons.append('موجودی محدود')
            
        return cons[:2]  # حداکثر 2 معایب

    def _assess_compatibility(self, product: Dict) -> str:
        """ارزیابی سازگاری محصول"""
        category = product.get('category', '')
        features = product.get('features_flat', '').lower()
        
        if 'لاستیک' in category:
            return 'بررسی سایز لاستیک با موتور ضروری'
        elif 'کلاه' in category:
            return 'انتخاب سایز مناسب سر ضروری'
        elif 'دستکش' in category:
            return 'انتخاب سایز مناسب دست ضروری'
        else:
            return 'سازگاری عمومی با اکثر موتورها'

    def _generate_recommendations(self, products: List[Dict], user_priorities: Optional[List[str]]) -> List[str]:
        """تولید توصیه‌های نهایی"""
        recommendations = []
        
        if not user_priorities:
            user_priorities = ['price', 'quality']
        
        if 'price' in user_priorities:
            cheapest = min(products, key=lambda x: x['price_numeric'] if x['price_numeric'] > 0 else float('inf'))
            recommendations.append(f"برای بودجه محدود: {cheapest['name']}")
        
        if 'quality' in user_priorities:
            highest_quality = max(products, key=lambda x: x['quality_score'])
            recommendations.append(f"برای کیفیت بالا: {highest_quality['name']}")
        
        best_value = max(products, key=lambda x: x['value_score'])
        recommendations.append(f"بهترین ارزش خرید: {best_value['name']}")
        
        return recommendations


class CompatibilityCheckTool(BaseModel):
    """بررسی سازگاری قطعات با موتور مشتری"""
    motorcycle_model: str = Field(..., description="مدل موتور مشتری")
    target_products: List[str] = Field(..., description="محصولات مورد بررسی")
    compatibility_type: str = Field(default="general", description="نوع بررسی سازگاری")

    async def __call__(self, rdb):
        compatibility_results = {
            "motorcycle_model": self.motorcycle_model,
            "total_products": len(self.target_products),
            "compatibility_analysis": [],
            "overall_compatibility": "unknown",
            "recommendations": [],
            "warnings": []
        }

        compatible_count = 0
        
        for product_name in self.target_products:
            # جستجوی محصول
            query_vector = await get_embedding(product_name)
            results = await search_hybrid_db(rdb, query_vector, product_name, top_k=3)
            
            if not results:
                compatibility_results["compatibility_analysis"].append({
                    "product": product_name,
                    "status": "not_found",
                    "compatibility": "unknown",
                    "confidence": 0.0,
                    "notes": "محصول در پایگاه داده یافت نشد"
                })
                continue

            best_match = results[0]
            metadata = best_match.get('metadata', {})
            
            # بررسی سازگاری
            compatibility_check = self._check_compatibility(
                self.motorcycle_model, 
                metadata, 
                product_name
            )
            
            if compatibility_check["compatibility"] in ["compatible", "likely_compatible"]:
                compatible_count += 1
            
            compatibility_results["compatibility_analysis"].append(compatibility_check)

        # تعیین سازگاری کلی
        compatibility_ratio = compatible_count / len(self.target_products) if self.target_products else 0
        
        if compatibility_ratio >= 0.8:
            compatibility_results["overall_compatibility"] = "highly_compatible"
        elif compatibility_ratio >= 0.6:
            compatibility_results["overall_compatibility"] = "mostly_compatible"
        elif compatibility_ratio >= 0.4:
            compatibility_results["overall_compatibility"] = "partially_compatible"
        else:
            compatibility_results["overall_compatibility"] = "low_compatibility"

        # تولید توصیه‌ها و هشدارها
        compatibility_results["recommendations"] = self._generate_compatibility_recommendations(
            compatibility_results["compatibility_analysis"]
        )
        compatibility_results["warnings"] = self._generate_warnings(
            compatibility_results["compatibility_analysis"]
        )

        return json.dumps(compatibility_results, ensure_ascii=False)

    def _check_compatibility(self, motorcycle_model: str, product_metadata: Dict, product_name: str) -> Dict:
        """بررسی سازگاری یک محصول با موتور"""
        category = product_metadata.get('category', '').lower()
        features = product_metadata.get('features_flat', '').lower()
        name = product_metadata.get('name', '').lower()
        
        motorcycle_lower = motorcycle_model.lower()
        
        # قوانین سازگاری بر اساس دسته‌بندی
        if 'لاستیک' in category:
            return self._check_tire_compatibility(motorcycle_lower, product_metadata)
        elif 'کلاه' in category:
            return self._check_helmet_compatibility(motorcycle_lower, product_metadata)
        elif 'دستکش' in category or 'پوشاک' in category:
            return self._check_apparel_compatibility(motorcycle_lower, product_metadata)
        elif 'پروتکشن' in category:
            return self._check_protection_compatibility(motorcycle_lower, product_metadata)
        else:
            return self._check_general_compatibility(motorcycle_lower, product_metadata)

    def _check_tire_compatibility(self, motorcycle: str, metadata: Dict) -> Dict:
        """بررسی سازگاری لاستیک"""
        name = metadata.get('name', '').lower()
        features = metadata.get('features_flat', '').lower()
        
        # استخراج سایز لاستیک از نام
        tire_size_pattern = r'(\d{3})[/\\](\d{2})[/\\](\d{2})'
        size_match = re.search(tire_size_pattern, name)
        
        if size_match:
            width, profile, rim = size_match.groups()
            
            # قوانین سازگاری برای موتورهای مختلف
            compatibility_rules = {
                'کلیک': {'width': ['110', '120', '130'], 'rim': ['10', '12', '14']},
                'آیروکس': {'width': ['110', '120', '130'], 'rim': ['10', '12', '14']},
                'هیوسانگ': {'width': ['110', '120'], 'rim': ['16', '17']},
                'آپاچی': {'width': ['120', '140'], 'rim': ['17', '18']},
                'بنلی': {'width': ['120', '140'], 'rim': ['17', '18']}
            }
            
            for bike_type, rules in compatibility_rules.items():
                if bike_type in motorcycle:
                    if width in rules['width'] and rim in rules['rim']:
                        return {
                            "product": metadata.get('name', ''),
                            "status": "analyzed",
                            "compatibility": "compatible",
                            "confidence": 0.9,
                            "notes": f"سایز {width}/{profile}/{rim} با {bike_type} سازگار است"
                        }
                    else:
                        return {
                            "product": metadata.get('name', ''),
                            "status": "analyzed", 
                            "compatibility": "incompatible",
                            "confidence": 0.8,
                            "notes": f"سایز {width}/{profile}/{rim} با {bike_type} سازگار نیست"
                        }
        
        return {
            "product": metadata.get('name', ''),
            "status": "analyzed",
            "compatibility": "needs_verification",
            "confidence": 0.5,
            "notes": "نیاز به بررسی دقیق‌تر سایز لاستیک"
        }

    def _check_helmet_compatibility(self, motorcycle: str, metadata: Dict) -> Dict:
        """بررسی سازگاری کلاه کاسکت"""
        features = metadata.get('features_flat', '').lower()
        
        if 'کراسی' in features or 'آفرود' in features:
            if any(term in motorcycle for term in ['کراس', 'آفرود', 'دوال']):
                compatibility = "compatible"
                confidence = 0.9
                notes = "کلاه کراسی برای موتور آفرود مناسب است"
            else:
                compatibility = "partially_compatible"
                confidence = 0.6
                notes = "کلاه کراسی برای شهری کاملاً مناسب نیست"
        elif 'شهری' in features or 'اسپرت' in features:
            compatibility = "compatible"
            confidence = 0.8
            notes = "کلاه برای استفاده شهری مناسب است"
        else:
            compatibility = "likely_compatible"
            confidence = 0.7
            notes = "کلاه معمولی برای اکثر موتورها مناسب است"

        return {
            "product": metadata.get('name', ''),
            "status": "analyzed",
            "compatibility": compatibility,
            "confidence": confidence,
            "notes": notes
        }

    def _check_apparel_compatibility(self, motorcycle: str, metadata: Dict) -> Dict:
        """بررسی سازگاری پوشاک"""
        return {
            "product": metadata.get('name', ''),
            "status": "analyzed",
            "compatibility": "compatible",
            "confidence": 0.9,
            "notes": "پوشاک موتورسواری با همه انواع موتور سازگار است"
        }

    def _check_protection_compatibility(self, motorcycle: str, metadata: Dict) -> Dict:
        """بررسی سازگاری پروتکشن"""
        name = metadata.get('name', '').lower()
        
        if 'کلیک' in name and 'کلیک' in motorcycle:
            compatibility = "compatible"
            confidence = 0.95
            notes = "پروتکشن مخصوص کلیک"
        elif 'آیروکس' in name and 'آیروکس' in motorcycle:
            compatibility = "compatible"
            confidence = 0.95
            notes = "پروتکشن مخصوص آیروکس"
        else:
            compatibility = "needs_verification"
            confidence = 0.6
            notes = "نیاز به بررسی سازگاری با مدل موتور"

        return {
            "product": metadata.get('name', ''),
            "status": "analyzed",
            "compatibility": compatibility,
            "confidence": confidence,
            "notes": notes
        }

    def _check_general_compatibility(self, motorcycle: str, metadata: Dict) -> Dict:
        """بررسی سازگاری عمومی"""
        return {
            "product": metadata.get('name', ''),
            "status": "analyzed",
            "compatibility": "likely_compatible",
            "confidence": 0.7,
            "notes": "احتمال سازگاری بالا - توصیه به مشورت با فروشنده"
        }

    def _generate_compatibility_recommendations(self, analysis: List[Dict]) -> List[str]:
        """تولید توصیه‌های سازگاری"""
        recommendations = []
        
        compatible_products = [a for a in analysis if a.get('compatibility') == 'compatible']
        if compatible_products:
            recommendations.append(f"{len(compatible_products)} محصول کاملاً سازگار یافت شد")
        
        needs_verification = [a for a in analysis if a.get('compatibility') == 'needs_verification']
        if needs_verification:
            recommendations.append(f"{len(needs_verification)} محصول نیاز به بررسی بیشتر دارد")
        
        incompatible = [a for a in analysis if a.get('compatibility') == 'incompatible']
        if incompatible:
            recommendations.append(f"{len(incompatible)} محصول سازگار نیست")
        
        return recommendations

    def _generate_warnings(self, analysis: List[Dict]) -> List[str]:
        """تولید هشدارهای سازگاری"""
        warnings = []
        
        for item in analysis:
            if item.get('compatibility') == 'incompatible':
                warnings.append(f"⚠️ {item['product']}: {item.get('notes', 'عدم سازگاری')}")
            elif item.get('confidence', 0) < 0.6:
                warnings.append(f"⚠️ {item['product']}: نیاز به تأیید سازگاری")
        
        return warnings


class CrossSellTool(BaseModel):
    """پیشنهاد محصولات مکمل بر اساس خرید اصلی"""
    main_product_category: str = Field(..., description="دسته اصلی محصول خریداری شده")
    budget_remaining: Optional[float] = Field(None, description="بودجه باقیمانده مشتری")
    customer_type: str = Field(default="general", description="نوع مشتری")
    purchase_intent: str = Field(default="immediate", description="قصد خرید")

    async def __call__(self, rdb):
        cross_sell_rules = {
            'کلاه کاسکت': ['دستکش', 'کاپشن', 'شاخ کلاه', 'پروتکشن'],
            'لاستیک موتور سیکلت': ['تیوب', 'والو', 'ابزار تعمیر', 'پمپ باد'],
            'پوشاک موتورسواری': ['کلاه کاسکت', 'دستکش', 'کفش', 'پروتکشن'],
            'پروتکشن موتور سیکلت': ['دستکش', 'کلاه کاسکت', 'کاپشن'],
            'باکس موتور سیکلت': ['قفل', 'بند نگهدارنده', 'کاور'],
            'لوازم جانبی موتورسیکلت': ['ابزار', 'تمیزکننده', 'روغن']
        }

        complementary_categories = cross_sell_rules.get(self.main_product_category, [])
        
        if not complementary_categories:
            return json.dumps({
                "main_category": self.main_product_category,
                "complementary_products": [],
                "message": "محصول مکمل خاصی برای این دسته‌بندی تعریف نشده"
            }, ensure_ascii=False)

        cross_sell_results = {
            "main_category": self.main_product_category,
            "budget_remaining": self.budget_remaining,
            "complementary_categories": complementary_categories,
            "recommendations": [],
            "total_suggested_value": 0,
            "priority_items": [],
            "optional_items": []
        }

        for category in complementary_categories[:3]:  # حداکثر 3 دسته مکمل
            # جستجوی محصولات در هر دسته
            query_vector = await get_embedding(category)
            results = await search_hybrid_db(
                rdb, 
                query_vector, 
                category, 
                top_k=5, 
                category=category
            )

            if results:
                best_product = results[0].get('metadata', {})
                price_numeric = best_product.get('price_numeric', 0)
                
                recommendation = {
                    "category": category,
                    "product_name": best_product.get('name', 'نامشخص'),
                    "brand": best_product.get('brand', 'نامشخص'),
                    "price": best_product.get('price', 'نامشخص'),
                    "price_numeric": price_numeric,
                    "image": best_product.get('image', ''),
                    "link": best_product.get('link', ''),
                    "priority": self._determine_priority(category, self.main_product_category),
                    "reason": self._get_cross_sell_reason(category, self.main_product_category),
                    "fits_budget": self.budget_remaining is None or price_numeric <= self.budget_remaining
                }

                cross_sell_results["recommendations"].append(recommendation)
                cross_sell_results["total_suggested_value"] += price_numeric

                # تقسیم‌بندی بر اساس اولویت
                if recommendation["priority"] == "high":
                    cross_sell_results["priority_items"].append(recommendation)
                else:
                    cross_sell_results["optional_items"].append(recommendation)

        # مرتب‌سازی بر اساس اولویت و قیمت
        cross_sell_results["priority_items"].sort(key=lambda x: x["price_numeric"])
        cross_sell_results["optional_items"].sort(key=lambda x: x["price_numeric"])

        return json.dumps(cross_sell_results, ensure_ascii=False)

    def _determine_priority(self, complement_category: str, main_category: str) -> str:
        """تعیین اولویت محصول مکمل"""
        high_priority_combinations = {
            'کلاه کاسکت': ['دستکش', 'پروتکشن'],
            'لاستیک موتور سیکلت': ['تیوب'],
            'پوشاک موتورسواری': ['کلاه کاسکت', 'دستکش'],
        }
        
        if main_category in high_priority_combinations:
            if complement_category in high_priority_combinations[main_category]:
                return "high"
        
        return "medium"

    def _get_cross_sell_reason(self, complement_category: str, main_category: str) -> str:
        """دلیل پیشنهاد محصول مکمل"""
        reasons = {
            ('کلاه کاسکت', 'دستکش'): 'برای محافظت کامل دست‌ها ضروری است',
            ('کلاه کاسکت', 'کاپشن'): 'برای محافظت بدن در سفرهای طولانی',
            ('لاستیک موتور سیکلت', 'تیوب'): 'برای نصب لاستیک جدید ضروری است',
            ('پوشاک موتورسواری', 'کلاه کاسکت'): 'برای ایمنی کامل سر ضروری است',
            ('پروتکشن موتور سیکلت', 'دستکش'): 'برای محافظت کامل دست‌ها',
        }
        
        return reasons.get((main_category, complement_category), f'محصول مکمل مناسب برای {main_category}')


class StockAnalyticsTool(BaseModel):
    """تحلیل موجودی و پیش‌بینی تقاضا"""
    category: str = Field(..., description="دسته‌بندی مورد تحلیل")
    time_horizon: str = Field(default="1_week", description="بازه زمانی پیش‌بینی")
    analysis_type: str = Field(default="availability", description="نوع تحلیل")

    async def __call__(self, rdb):
        # جستجوی تمام محصولات در دسته
        query_vector = await get_embedding(self.category)
        results = await search_hybrid_db(
            rdb, 
            query_vector, 
            self.category, 
            top_k=50,  # تحلیل موجودی نیاز به نمونه بیشتر دارد
            category=self.category
        )

        if not results:
            return json.dumps({
                "category": self.category,
                "message": "محصولی در این دسته یافت نشد",
                "analysis": {}
            }, ensure_ascii=False)

        stock_analysis = {
            "category": self.category,
            "analysis_date": datetime.now().isoformat(),
            "total_products": len(results),
            "stock_summary": {
                "in_stock": 0,
                "low_stock": 0,
                "out_of_stock": 0,
                "unlimited_stock": 0
            },
            "price_analysis": {
                "min_price": float('inf'),
                "max_price": 0,
                "avg_price": 0,
                "price_ranges": {
                    "budget": 0,      # زیر 5 میلیون
                    "mid_range": 0,   # 5-10 میلیون
                    "premium": 0      # بالای 10 میلیون
                }
            },
            "brand_distribution": {},
            "alerts": [],
            "recommendations": []
        }

        total_price = 0
        prices = []

        for result in results:
            metadata = result.get('metadata', {})
            stock = metadata.get('stock', 'نامشخص')
            price_numeric = metadata.get('price_numeric', 0)
            brand = metadata.get('brand', 'نامشخص')

            # تحلیل موجودی
            if 'موجود' in stock and 'انبار' in stock:
                if any(char.isdigit() and int(char) <= settings.STOCK_ALERT_THRESHOLD for char in stock):
                    stock_analysis["stock_summary"]["low_stock"] += 1
                    stock_analysis["alerts"].append(f"⚠️ موجودی کم: {metadata.get('name', 'نامشخص')}")
                else:
                    stock_analysis["stock_summary"]["in_stock"] += 1
            elif 'موجود' in stock:
                stock_analysis["stock_summary"]["unlimited_stock"] += 1
            else:
                stock_analysis["stock_summary"]["out_of_stock"] += 1

            # تحلیل قیمت
            if price_numeric > 0:
                prices.append(price_numeric)
                total_price += price_numeric
                
                if price_numeric < stock_analysis["price_analysis"]["min_price"]:
                    stock_analysis["price_analysis"]["min_price"] = price_numeric
                if price_numeric > stock_analysis["price_analysis"]["max_price"]:
                    stock_analysis["price_analysis"]["max_price"] = price_numeric

                # تقسیم‌بندی قیمتی
                if price_numeric < 5000000:
                    stock_analysis["price_analysis"]["price_ranges"]["budget"] += 1
                elif price_numeric < 10000000:
                    stock_analysis["price_analysis"]["price_ranges"]["mid_range"] += 1
                else:
                    stock_analysis["price_analysis"]["price_ranges"]["premium"] += 1

            # توزیع برند
            stock_analysis["brand_distribution"][brand] = stock_analysis["brand_distribution"].get(brand, 0) + 1

        # محاسبه میانگین قیمت
        if prices:
            stock_analysis["price_analysis"]["avg_price"] = total_price / len(prices)

        # تولید توصیه‌ها
        stock_analysis["recommendations"] = self._generate_stock_recommendations(stock_analysis)

        return json.dumps(stock_analysis, ensure_ascii=False)

    def _generate_stock_recommendations(self, analysis: Dict) -> List[str]:
        """تولید توصیه‌های موجودی"""
        recommendations = []
        
        stock_summary = analysis["stock_summary"]
        
        if stock_summary["low_stock"] > 0:
            recommendations.append(f"نیاز به تأمین مجدد {stock_summary['low_stock']} محصول")
        
        if stock_summary["out_of_stock"] > 0:
            recommendations.append(f"{stock_summary['out_of_stock']} محصول ناموجود - بررسی تأمین‌کننده")
        
        # تحلیل قیمتی
        price_ranges = analysis["price_analysis"]["price_ranges"]
        total_products = sum(price_ranges.values())
        
        if total_products > 0:
            budget_percentage = price_ranges["budget"] / total_products * 100
            if budget_percentage < 30:
                recommendations.append("نیاز به محصولات بیشتر در رنج قیمت اقتصادی")
        
        # تحلیل برند
        brand_dist = analysis["brand_distribution"]
        if len(brand_dist) > 1:
            dominant_brand = max(brand_dist, key=brand_dist.get)
            if brand_dist[dominant_brand] / sum(brand_dist.values()) > 0.6:
                recommendations.append(f"تنوع برند کم - برند {dominant_brand} غالب است")
        
        return recommendations

