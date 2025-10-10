"""
سیستم جلوگیری از توهم (Hallucination Prevention) در پاسخ‌های چت‌بات
"""
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class HallucinationType(Enum):
    FACTUAL_ERROR = "factual_error"
    PRODUCT_NOT_EXISTS = "product_not_exists"
    PRICE_MISMATCH = "price_mismatch"
    SPECIFICATION_ERROR = "specification_error"
    BRAND_ERROR = "brand_error"
    CATEGORY_ERROR = "category_error"

class ConfidenceLevel(Enum):
    HIGH = "high"  # 0.8-1.0
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"  # 0.0-0.5

@dataclass
class HallucinationCheck:
    type: HallucinationType
    confidence: float
    message: str
    suggestion: str
    source_data: Optional[Dict] = None

class HallucinationPreventionSystem:
    def __init__(self):
        self.knowledge_base_products = set()  # لیست محصولات موجود در نالج بیس
        self.valid_brands = {
            "state", "scoico", "agv", "shoei", "arai", "bell", "hjc", "ls2",
            "alpinestars", "dainese", "revit", "richa", "oxford", "spidi",
            "mxs", "maxxis", "michelin", "bridgestone", "continental",
            "yamaha", "honda", "kawasaki", "suzuki", "ducati", "bmw"
        }
        
        self.valid_categories = {
            "کلاه کاسکت", "پوشاک موتورسواری", "لاستیک موتور سیکلت",
            "پروتکشن موتور سیکلت", "باکس موتور سیکلت", "لوازم جانبی موتورسیکلت",
            "لوازم کلاه کاسکت", "لوازم کلیک و طرح کلیک", 
            "لوازم آیروکس و طرح آیروکس (NVX)", "روغن موتور", "روغن ترمز"
        }
        
        self.valid_sizes = {
            "xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl",
            "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48"
        }

    async def validate_response(self, 
                              response_text: str, 
                              knowledge_base_results: Dict[str, Any],
                              original_query: str) -> Tuple[bool, List[HallucinationCheck]]:
        """
        اعتبارسنجی کامل پاسخ برای جلوگیری از توهم
        """
        checks = []
        
        # 1. بررسی محصولات ذکر شده در پاسخ
        product_checks = await self._check_mentioned_products(response_text, knowledge_base_results)
        checks.extend(product_checks)
        
        # 2. بررسی قیمت‌ها
        price_checks = await self._check_prices(response_text, knowledge_base_results)
        checks.extend(price_checks)
        
        # 3. بررسی برندها
        brand_checks = await self._check_brands(response_text)
        checks.extend(brand_checks)
        
        # 4. بررسی دسته‌بندی‌ها
        category_checks = await self._check_categories(response_text)
        checks.extend(category_checks)
        
        # 5. بررسی ویژگی‌های فنی
        spec_checks = await self._check_specifications(response_text, knowledge_base_results)
        checks.extend(spec_checks)
        
        # 6. بررسی اطلاعات کلی
        factual_checks = await self._check_factual_claims(response_text, original_query)
        checks.extend(factual_checks)
        
        # تعیین نهایی اعتبار پاسخ
        high_confidence_errors = [c for c in checks if c.confidence > 0.8]
        is_valid = len(high_confidence_errors) == 0
        
        return is_valid, checks

    async def _check_mentioned_products(self, response_text: str, knowledge_base_results: Dict) -> List[HallucinationCheck]:
        """
        بررسی محصولات ذکر شده در پاسخ
        """
        checks = []
        
        # استخراج نام محصولات از پاسخ
        product_patterns = [
            r'محصول\s+([^\n\r،.]+)',
            r'([A-Za-z0-9\s]+)\s+مدل\s+([^\n\r،.]+)',
            r'([^\n\r،.]+)\s+از\s+برند\s+([^\n\r،.]+)'
        ]
        
        mentioned_products = []
        for pattern in product_patterns:
            matches = re.findall(pattern, response_text)
            mentioned_products.extend(matches)
        
        # بررسی وجود محصولات در نالج بیس
        kb_products = knowledge_base_results.get('all_products', [])
        kb_product_names = {p.get('name', '').lower().strip() for p in kb_products}
        
        for product in mentioned_products:
            product_name = str(product).lower().strip()
            if product_name and product_name not in kb_product_names:
                # بررسی دقیق‌تر با fuzzy matching
                is_similar = await self._fuzzy_match_product(product_name, kb_product_names)
                if not is_similar:
                    checks.append(HallucinationCheck(
                        type=HallucinationType.PRODUCT_NOT_EXISTS,
                        confidence=0.9,
                        message=f"محصول '{product}' در پایگاه داده موجود نیست",
                        suggestion="فقط محصولات موجود در نالج بیس را ذکر کنید",
                        source_data={"mentioned_product": product}
                    ))
        
        return checks

    async def _check_prices(self, response_text: str, knowledge_base_results: Dict) -> List[HallucinationCheck]:
        """
        بررسی قیمت‌های ذکر شده
        """
        checks = []
        
        # استخراج قیمت‌ها از پاسخ
        price_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:تومان|تومن|ت)'
        mentioned_prices = re.findall(price_pattern, response_text)
        
        # قیمت‌های موجود در نالج بیس
        kb_products = knowledge_base_results.get('all_products', [])
        kb_prices = [p.get('price_numeric', 0) for p in kb_products if p.get('price_numeric', 0) > 0]
        
        for price_str in mentioned_prices:
            try:
                price_value = float(price_str.replace(',', ''))
                
                # بررسی نزدیکی قیمت با قیمت‌های موجود (حداکثر 50% اختلاف)
                if kb_prices:
                    min_kb_price = min(kb_prices)
                    max_kb_price = max(kb_prices)
                    
                    if price_value < min_kb_price * 0.5 or price_value > max_kb_price * 1.5:
                        checks.append(HallucinationCheck(
                            type=HallucinationType.PRICE_MISMATCH,
                            confidence=0.8,
                            message=f"قیمت {price_value:,} تومان خارج از محدوده قیمت‌های موجود است",
                            suggestion="فقط قیمت‌های موجود در نالج بیس را ذکر کنید",
                            source_data={"mentioned_price": price_value, "kb_price_range": [min_kb_price, max_kb_price]}
                        ))
            except ValueError:
                continue
        
        return checks

    async def _check_brands(self, response_text: str) -> List[HallucinationCheck]:
        """
        بررسی برندهای ذکر شده
        """
        checks = []
        
        # استخراج برندها از پاسخ
        brand_pattern = r'برند\s+([A-Za-z0-9\s]+)|([A-Za-z]+)\s+از\s+برند'
        brand_matches = re.findall(brand_pattern, response_text)
        
        for match in brand_matches:
            brand = (match[0] or match[1]).strip().lower()
            if brand and brand not in self.valid_brands:
                # بررسی fuzzy matching
                similar_brand = await self._find_similar_brand(brand)
                if not similar_brand:
                    checks.append(HallucinationCheck(
                        type=HallucinationType.BRAND_ERROR,
                        confidence=0.7,
                        message=f"برند '{brand}' در لیست برندهای معتبر نیست",
                        suggestion="فقط برندهای موجود در نالج بیس را ذکر کنید",
                        source_data={"mentioned_brand": brand}
                    ))
        
        return checks

    async def _check_categories(self, response_text: str) -> List[HallucinationCheck]:
        """
        بررسی دسته‌بندی‌های ذکر شده
        """
        checks = []
        
        # استخراج دسته‌بندی‌ها
        for category in self.valid_categories:
            if category in response_text:
                continue  # دسته‌بندی معتبر است
        
        # بررسی دسته‌بندی‌های غیرمعتبر
        invalid_category_patterns = [
            r'دسته‌بندی\s+([^\n\r،.]+)',
            r'در\s+رده\s+([^\n\r،.]+)',
            r'از\s+دسته\s+([^\n\r،.]+)'
        ]
        
        for pattern in invalid_category_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                if match.strip() not in self.valid_categories:
                    checks.append(HallucinationCheck(
                        type=HallucinationType.CATEGORY_ERROR,
                        confidence=0.6,
                        message=f"دسته‌بندی '{match}' معتبر نیست",
                        suggestion="فقط دسته‌بندی‌های موجود در نالج بیس را استفاده کنید",
                        source_data={"mentioned_category": match}
                    ))
        
        return checks

    async def _check_specifications(self, response_text: str, knowledge_base_results: Dict) -> List[HallucinationCheck]:
        """
        بررسی ویژگی‌های فنی ذکر شده
        """
        checks = []
        
        # استخراج ویژگی‌های فنی
        spec_patterns = [
            r'سایز\s+([A-Za-z0-9]+)',
            r'پهنا\s+(\d+)\s*میلی‌متر',
            r'وزن\s+(\d+)\s*گرم',
            r'جنس\s+([^\n\r،.]+)',
            r'رنگ\s+([^\n\r،.]+)'
        ]
        
        kb_products = knowledge_base_results.get('all_products', [])
        kb_features = []
        for product in kb_products:
            features = product.get('features', '')
            if isinstance(features, str):
                kb_features.append(features.lower())
        
        kb_features_text = ' '.join(kb_features)
        
        for pattern in spec_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                if not self._is_specification_valid(match, kb_features_text):
                    checks.append(HallucinationCheck(
                        type=HallucinationType.SPECIFICATION_ERROR,
                        confidence=0.6,
                        message=f"ویژگی '{match}' در محصولات موجود یافت نشد",
                        suggestion="فقط ویژگی‌های موجود در نالج بیس را ذکر کنید",
                        source_data={"mentioned_spec": match}
                    ))
        
        return checks

    async def _check_factual_claims(self, response_text: str, original_query: str) -> List[HallucinationCheck]:
        """
        بررسی ادعاهای کلی و واقعی
        """
        checks = []
        
        # الگوهای ادعاهای مشکوک
        suspicious_patterns = [
            r'همیشه\s+([^\n\r،.]+)',
            r'هرگز\s+([^\n\r،.]+)',
            r'حتماً\s+([^\n\r،.]+)',
            r'مطمئناً\s+([^\n\r،.]+)',
            r'قطعاً\s+([^\n\r،.]+)'
        ]
        
        for pattern in suspicious_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                checks.append(HallucinationCheck(
                    type=HallucinationType.FACTUAL_ERROR,
                    confidence=0.5,
                    message=f"ادعای قطعی '{match}' ممکن است نادرست باشد",
                    suggestion="از ادعاهای قطعی خودداری کنید و فقط اطلاعات موجود در نالج بیس را ارائه دهید",
                    source_data={"claimed_fact": match}
                ))
        
        return checks

    async def _fuzzy_match_product(self, product_name: str, kb_product_names: set) -> bool:
        """
        تطبیق فازی محصول با محصولات موجود
        """
        # تطبیق ساده بر اساس کلمات کلیدی
        product_words = set(product_name.split())
        
        for kb_product in kb_product_names:
            kb_words = set(kb_product.split())
            # اگر 70% کلمات مشترک باشند
            if len(product_words & kb_words) / len(product_words) > 0.7:
                return True
        
        return False

    async def _find_similar_brand(self, brand: str) -> Optional[str]:
        """
        یافتن برند مشابه در لیست برندهای معتبر
        """
        brand_lower = brand.lower()
        
        for valid_brand in self.valid_brands:
            if brand_lower in valid_brand or valid_brand in brand_lower:
                return valid_brand
        
        return None

    def _is_specification_valid(self, spec: str, kb_features_text: str) -> bool:
        """
        بررسی اعتبار ویژگی فنی
        """
        spec_lower = spec.lower()
        return spec_lower in kb_features_text

    def generate_safe_response(self, 
                             original_response: str, 
                             checks: List[HallucinationCheck],
                             knowledge_base_results: Dict) -> str:
        """
        تولید پاسخ ایمن با حذف بخش‌های مشکوک
        """
        if not checks:
            return original_response
        
        # اگر خطاهای با اعتماد بالا وجود دارد، پاسخ را محدود کن
        high_confidence_errors = [c for c in checks if c.confidence > 0.8]
        
        if high_confidence_errors:
            safe_response = "بر اساس اطلاعات موجود در پایگاه داده:\n\n"
            
            # فقط محصولات موجود در نالج بیس را نمایش بده
            kb_products = knowledge_base_results.get('all_products', [])
            if kb_products:
                for i, product in enumerate(kb_products[:10], 1):  # حداکثر 10 محصول
                    safe_response += f"{i}. {product.get('name', 'نامشخص')}\n"
                    safe_response += f"   قیمت: {product.get('price', 'نامشخص')}\n"
                    safe_response += f"   برند: {product.get('brand', 'نامشخص')}\n\n"
            else:
                safe_response += "متأسفانه محصولی مطابق درخواست شما یافت نشد."
            
            safe_response += "\n⚠️ توجه: این پاسخ فقط بر اساس اطلاعات موجود در پایگاه داده ارائه شده است."
            return safe_response
        
        # اگر خطاهای متوسط وجود دارد، هشدار اضافه کن
        medium_confidence_errors = [c for c in checks if c.confidence > 0.5]
        if medium_confidence_errors:
            warning = "\n⚠️ هشدار: برخی اطلاعات ممکن است نیاز به تأیید داشته باشند. لطفاً با اطلاعات موجود در پایگاه داده تطبیق دهید."
            return original_response + warning
        
        return original_response

    def get_confidence_score(self, checks: List[HallucinationCheck]) -> float:
        """
        محاسبه نمره اعتماد کلی پاسخ
        """
        if not checks:
            return 1.0
        
        # میانگین وزن‌دار بر اساس نوع خطا
        total_weight = 0
        weighted_sum = 0
        
        for check in checks:
            weight = 1.0
            if check.type == HallucinationType.PRODUCT_NOT_EXISTS:
                weight = 2.0  # خطای جدی
            elif check.type == HallucinationType.PRICE_MISMATCH:
                weight = 1.5
            
            weighted_sum += check.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 1.0
        
        confidence = 1.0 - (weighted_sum / total_weight)
        return max(0.0, confidence)
