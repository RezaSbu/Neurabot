from typing import Dict, List, Any, Optional, Callable, Tuple
import asyncio
import json
from datetime import datetime
from enum import Enum

from app.memory.customer_profile import CustomerProfile
from app.intelligence.business_logic import BusinessIntelligence, QueryIntent
from app.search.enhanced_search import EnhancedSearchEngine
from app.assistants.advanced_tools import (
    ProductComparisonTool, 
    CompatibilityCheckTool, 
    CrossSellTool, 
    StockAnalyticsTool
)

class ReasoningStep(Enum):
    """مراحل زنجیره استدلال"""
    UNDERSTAND_NEED = "understand_need"
    GATHER_REQUIREMENTS = "gather_requirements"  
    SEARCH_AND_FILTER = "search_and_filter"
    ANALYZE_OPTIONS = "analyze_options"
    MAKE_RECOMMENDATIONS = "make_recommendations"
    SUGGEST_COMPLEMENTARY = "suggest_complementary"
    PROVIDE_GUIDANCE = "provide_guidance"
    VALIDATE_RESULTS = "validate_results"

class ReasoningContext:
    """Context برای نگهداری اطلاعات در طول زنجیره استدلال"""
    
    def __init__(self, original_query: str, user_profile: Optional[CustomerProfile] = None):
        self.original_query = original_query
        self.user_profile = user_profile
        self.steps_completed = []
        self.intermediate_results = {}
        self.confidence_scores = {}
        self.decision_factors = []
        self.warnings = []
        self.recommendations = []
        self.final_products = []
        self.reasoning_log = []
        
    def log_step(self, step: ReasoningStep, result: Any, confidence: float = 1.0):
        """ثبت نتیجه یک مرحله"""
        self.steps_completed.append(step)
        self.intermediate_results[step.value] = result
        self.confidence_scores[step.value] = confidence
        self.reasoning_log.append({
            "step": step.value,
            "timestamp": datetime.now().isoformat(),
            "confidence": confidence,
            "summary": self._summarize_step_result(step, result)
        })
    
    def _summarize_step_result(self, step: ReasoningStep, result: Any) -> str:
        """خلاصه نتیجه هر مرحله"""
        if step == ReasoningStep.UNDERSTAND_NEED:
            return f"نیاز شناسایی شد: {result.get('primary_need', 'نامشخص')}"
        elif step == ReasoningStep.SEARCH_AND_FILTER:
            return f"{len(result)} محصول یافت شد"
        elif step == ReasoningStep.ANALYZE_OPTIONS:
            return f"{len(result)} گزینه تحلیل شد"
        else:
            return f"مرحله {step.value} تکمیل شد"

class ReasoningChain:
    """زنجیره استدلال چندمرحله‌ای برای پردازش پیچیده query ها"""
    
    def __init__(self):
        self.business_intelligence = BusinessIntelligence()
        self.search_engine = EnhancedSearchEngine()
        self.step_handlers = {
            ReasoningStep.UNDERSTAND_NEED: self._understand_need,
            ReasoningStep.GATHER_REQUIREMENTS: self._gather_requirements,
            ReasoningStep.SEARCH_AND_FILTER: self._search_and_filter,
            ReasoningStep.ANALYZE_OPTIONS: self._analyze_options,
            ReasoningStep.MAKE_RECOMMENDATIONS: self._make_recommendations,
            ReasoningStep.SUGGEST_COMPLEMENTARY: self._suggest_complementary,
            ReasoningStep.PROVIDE_GUIDANCE: self._provide_guidance,
            ReasoningStep.VALIDATE_RESULTS: self._validate_results
        }

    async def process_complex_query(
        self, 
        query: str, 
        user_profile: Optional[CustomerProfile] = None,
        rdb = None
    ) -> Dict[str, Any]:
        """پردازش query پیچیده با استفاده از زنجیره استدلال"""
        
        context = ReasoningContext(query, user_profile)
        
        # تعیین مراحل مورد نیاز بر اساس نوع query
        required_steps = await self._determine_required_steps(query, user_profile)
        
        # اجرای مراحل به ترتیب
        for step in required_steps:
            try:
                handler = self.step_handlers[step]
                result = await handler(context, rdb)
                
                # محاسبه اعتماد بر اساس کیفیت نتیجه
                confidence = self._calculate_step_confidence(step, result, context)
                context.log_step(step, result, confidence)
                
                # اگر اعتماد خیلی پایین است، متوقف کن
                if confidence < 0.3 and step in [ReasoningStep.SEARCH_AND_FILTER]:
                    context.warnings.append(f"اعتماد پایین در مرحله {step.value}")
                    break
                    
            except Exception as e:
                context.warnings.append(f"خطا در مرحله {step.value}: {str(e)}")
                continue
        
        # تولید نتیجه نهایی
        return self._generate_final_result(context)

    async def _determine_required_steps(
        self, 
        query: str, 
        user_profile: Optional[CustomerProfile]
    ) -> List[ReasoningStep]:
        """تعیین مراحل مورد نیاز بر اساس نوع query"""
        
        # تحلیل intent برای تعیین مراحل
        intent_analysis = await self.business_intelligence.analyze_query_intent(
            query, {}, user_profile
        )
        
        primary_intent = intent_analysis['primary_intent']
        
        # مراحل پایه که همیشه اجرا می‌شوند
        base_steps = [
            ReasoningStep.UNDERSTAND_NEED,
            ReasoningStep.SEARCH_AND_FILTER,
        ]
        
        # مراحل اضافی بر اساس intent
        if primary_intent == QueryIntent.COMPARISON_SEEKING.value:
            base_steps.extend([
                ReasoningStep.ANALYZE_OPTIONS,
                ReasoningStep.MAKE_RECOMMENDATIONS
            ])
        elif primary_intent == QueryIntent.PURCHASE_READY.value:
            base_steps.extend([
                ReasoningStep.MAKE_RECOMMENDATIONS,
                ReasoningStep.SUGGEST_COMPLEMENTARY,
                ReasoningStep.PROVIDE_GUIDANCE
            ])
        elif primary_intent == QueryIntent.RESEARCH_PHASE.value:
            base_steps.extend([
                ReasoningStep.GATHER_REQUIREMENTS,
                ReasoningStep.ANALYZE_OPTIONS,
                ReasoningStep.MAKE_RECOMMENDATIONS
            ])
        elif primary_intent == QueryIntent.COMPATIBILITY_CHECK.value:
            base_steps.extend([
                ReasoningStep.ANALYZE_OPTIONS,
                ReasoningStep.VALIDATE_RESULTS
            ])
        else:
            # برای سایر intent ها
            base_steps.extend([
                ReasoningStep.MAKE_RECOMMENDATIONS
            ])
        
        # همیشه validation در انتها
        if ReasoningStep.VALIDATE_RESULTS not in base_steps:
            base_steps.append(ReasoningStep.VALIDATE_RESULTS)
        
        return base_steps

    async def _understand_need(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 1: درک نیاز کاربر"""
        
        query = context.original_query.lower()
        
        # تشخیص نوع محصول
        product_indicators = {
            'کلاه': 'کلاه کاسکت',
            'کاسکت': 'کلاه کاسکت', 
            'helmet': 'کلاه کاسکت',
            'دستکش': 'پوشاک موتورسواری',
            'glove': 'پوشاک موتورسواری',
            'لاستیک': 'لاستیک موتور سیکلت',
            'tire': 'لاستیک موتور سیکلت',
            'کاپشن': 'پوشاک موتورسواری',
            'jacket': 'پوشاک موتورسواری',
            'پروتکشن': 'پروتکشن موتور سیکلت',
            'protection': 'پروتکشن موتور سیکلت',
            'باکس': 'باکس موتور سیکلت',
            'box': 'باکس موتور سیکلت'
        }
        
        detected_category = None
        for indicator, category in product_indicators.items():
            if indicator in query:
                detected_category = category
                break
        
        # تشخیص intent خرید
        purchase_indicators = ['می‌خوام', 'بخرم', 'سفارش', 'خرید', 'نیاز دارم']
        has_purchase_intent = any(indicator in query for indicator in purchase_indicators)
        
        # تشخیص مقایسه
        comparison_indicators = ['مقایسه', 'بهتر', 'تفاوت', 'یا', 'در مقابل']
        wants_comparison = any(indicator in query for indicator in comparison_indicators)
        
        # تشخیص محدودیت بودجه
        budget_match = self._extract_budget_from_query(query)
        
        # تشخیص مدل موتور
        motorcycle_model = self._extract_motorcycle_model(query)
        
        return {
            'primary_need': detected_category or 'نامشخص',
            'purchase_intent': has_purchase_intent,
            'wants_comparison': wants_comparison,
            'budget_constraint': budget_match,
            'motorcycle_model': motorcycle_model,
            'urgency_level': self._assess_urgency_from_query(query),
            'technical_level': self._assess_technical_level(query)
        }

    def _extract_budget_from_query(self, query: str) -> Optional[Dict[str, float]]:
        """استخراج بودجه از query"""
        import re
        
        # الگوهای مختلف بودجه
        patterns = [
            r'تا\s+(\d+)\s*(میلیون|تومان|تومن)',
            r'حدود\s+(\d+)\s*(میلیون|تومان|تومن)',
            r'بودجه\s+(\d+)\s*(میلیون|تومان|تومن)',
            r'(\d+)\s*(میلیون|تومان|تومن)\s+دارم'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                
                if unit == 'میلیون':
                    max_budget = amount * 1000000
                elif unit in ['تومان', 'تومن']:
                    if amount <= 10:  # احتمالاً میلیون تومان منظور است
                        max_budget = amount * 1000000
                    else:
                        max_budget = amount * 1000
                else:
                    max_budget = amount
                
                return {'max': max_budget, 'flexibility': 0.2}  # 20% انعطاف
        
        return None

    def _extract_motorcycle_model(self, query: str) -> Optional[str]:
        """استخراج مدل موتور از query"""
        models = ['کلیک', 'آیروکس', 'هیوسانگ', 'آپاچی', 'بنلی', 'پولسار', 'هارلی']
        
        for model in models:
            if model in query:
                return model
        
        return None

    def _assess_urgency_from_query(self, query: str) -> str:
        """ارزیابی فوریت از query"""
        urgent_words = ['فوری', 'سریع', 'الان', 'امروز']
        
        if any(word in query for word in urgent_words):
            return 'high'
        elif any(word in query for word in ['زودتر', 'سریع‌تر']):
            return 'medium'
        else:
            return 'low'

    def _assess_technical_level(self, query: str) -> str:
        """ارزیابی سطح فنی از query"""
        technical_terms = ['سی‌سی', 'پهنا', 'پروفایل', 'DOT', 'ECE', 'ABS']
        beginner_terms = ['نمی‌دونم', 'چیه', 'چطور', 'راهنمایی']
        
        if any(term in query for term in technical_terms):
            return 'expert'
        elif any(term in query for term in beginner_terms):
            return 'beginner'
        else:
            return 'intermediate'

    async def _gather_requirements(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 2: جمع‌آوری نیازمندی‌ها"""
        
        need_analysis = context.intermediate_results.get('understand_need', {})
        
        requirements = {
            'must_have': [],
            'nice_to_have': [],
            'constraints': [],
            'preferences': []
        }
        
        # الزامات اساسی بر اساس نوع محصول
        primary_need = need_analysis.get('primary_need')
        if primary_need == 'کلاه کاسکت':
            requirements['must_have'].extend(['ایمنی', 'سایز مناسب'])
            requirements['nice_to_have'].extend(['طراحی زیبا', 'تهویه خوب'])
        elif primary_need == 'لاستیک موتور سیکلت':
            requirements['must_have'].extend(['سایز مناسب', 'کیفیت مناسب'])
            requirements['nice_to_have'].extend(['دوام بالا', 'چسبندگی خوب'])
        
        # محدودیت‌های بودجه
        if need_analysis.get('budget_constraint'):
            requirements['constraints'].append({
                'type': 'budget',
                'value': need_analysis['budget_constraint']
            })
        
        # ترجیحات بر اساس پروفایل کاربر
        if context.user_profile:
            if context.user_profile.preferred_brands:
                requirements['preferences'].append({
                    'type': 'brand',
                    'values': context.user_profile.preferred_brands
                })
            
            if context.user_profile.price_sensitivity == 'high':
                requirements['preferences'].append({
                    'type': 'price_focus',
                    'value': 'economical'
                })
        
        return requirements

    async def _search_and_filter(self, context: ReasoningContext, rdb) -> List[Dict[str, Any]]:
        """مرحله 3: جستجو و فیلتر"""
        
        need_analysis = context.intermediate_results.get('understand_need', {})
        
        # تنظیم پارامترهای جستجو
        search_params = {
            'query': context.original_query,
            'category': need_analysis.get('primary_need'),
            'user_profile': context.user_profile
        }
        
        # اعمال فیلترهای بودجه
        budget_constraint = need_analysis.get('budget_constraint')
        if budget_constraint:
            search_params['filters'] = {
                'budget_range': self._convert_budget_to_range(budget_constraint)
            }
        
        # جستجوی پیشرفته
        try:
            results = await self.search_engine.semantic_search_with_reranking(
                **search_params
            )
            
            # فیلتر اضافی بر اساس نیازمندی‌ها
            requirements = context.intermediate_results.get('gather_requirements', {})
            if requirements:
                results = self._apply_requirements_filter(results, requirements)
            
            return results
            
        except Exception as e:
            context.warnings.append(f"خطا در جستجو: {str(e)}")
            return []

    def _convert_budget_to_range(self, budget_constraint: Dict[str, float]) -> str:
        """تبدیل محدودیت بودجه به رنج"""
        max_budget = budget_constraint.get('max', 0)
        
        if max_budget < 5000000:
            return "زیر ۵ میلیون"
        elif max_budget < 10000000:
            return "۵-۱۰ میلیون"
        elif max_budget < 20000000:
            return "۱۰-۲۰ میلیون"
        else:
            return "بیش از ۲۰ میلیون"

    def _apply_requirements_filter(
        self, 
        results: List[Dict[str, Any]], 
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """اعمال فیلتر نیازمندی‌ها"""
        
        filtered_results = []
        
        for result in results:
            metadata = result.get('metadata', {})
            
            # بررسی الزامات اساسی
            meets_requirements = True
            must_have = requirements.get('must_have', [])
            
            for requirement in must_have:
                if requirement == 'سایز مناسب':
                    # بررسی وجود سایز
                    variations = metadata.get('variations', [])
                    if not variations or not any(v.get('size') for v in variations):
                        meets_requirements = False
                        break
            
            if meets_requirements:
                # محاسبه امتیاز nice-to-have
                nice_score = 0
                nice_to_have = requirements.get('nice_to_have', [])
                features = metadata.get('features_flat', '').lower()
                
                for nice_req in nice_to_have:
                    if nice_req.lower() in features:
                        nice_score += 1
                
                result['requirements_score'] = nice_score / max(len(nice_to_have), 1)
                filtered_results.append(result)
        
        return filtered_results

    async def _analyze_options(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 4: تحلیل گزینه‌ها"""
        
        search_results = context.intermediate_results.get('search_and_filter', [])
        
        if not search_results:
            return {'analysis': 'no_products_found', 'recommendations': []}
        
        # اگر بیش از 2 محصول داریم، مقایسه انجام دهیم
        if len(search_results) >= 2:
            # انتخاب محصولات برتر برای مقایسه
            top_products = search_results[:min(5, len(search_results))]
            product_ids = [
                result.get('metadata', {}).get('product_id', '') 
                for result in top_products
            ]
            product_ids = [pid for pid in product_ids if pid]
            
            if len(product_ids) >= 2:
                # استفاده از ابزار مقایسه
                comparison_tool = ProductComparisonTool(
                    product_ids=product_ids,
                    comparison_criteria=["price", "quality", "compatibility", "features"]
                )
                
                try:
                    comparison_result = await comparison_tool(rdb)
                    comparison_data = json.loads(comparison_result)
                    
                    return {
                        'analysis_type': 'comparative',
                        'comparison_data': comparison_data,
                        'top_choice': comparison_data.get('summary', {}).get('best_value'),
                        'alternatives': comparison_data.get('products', [])
                    }
                    
                except Exception as e:
                    context.warnings.append(f"خطا در مقایسه: {str(e)}")
        
        # تحلیل ساده برای محصولات کم
        return self._simple_analysis(search_results)

    def _simple_analysis(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تحلیل ساده محصولات"""
        
        if not products:
            return {'analysis_type': 'none', 'message': 'محصولی یافت نشد'}
        
        # مرتب‌سازی بر اساس امتیاز
        sorted_products = sorted(
            products, 
            key=lambda x: x.get('final_score', x.get('combined_score', x.get('score', 0))),
            reverse=True
        )
        
        best_product = sorted_products[0]
        
        analysis = {
            'analysis_type': 'simple',
            'best_choice': best_product.get('metadata', {}).get('name', 'نامشخص'),
            'reason': self._generate_selection_reason(best_product),
            'alternatives': []
        }
        
        # اضافه کردن گزینه‌های جایگزین
        if len(sorted_products) > 1:
            analysis['alternatives'] = [
                {
                    'name': p.get('metadata', {}).get('name', 'نامشخص'),
                    'reason': self._generate_alternative_reason(p, best_product)
                }
                for p in sorted_products[1:3]  # 2 جایگزین
            ]
        
        return analysis

    def _generate_selection_reason(self, product: Dict[str, Any]) -> str:
        """تولید دلیل انتخاب محصول"""
        metadata = product.get('metadata', {})
        factors = []
        
        # عوامل امتیاز‌دهی
        if product.get('personalization_factors'):
            factors.extend(product['personalization_factors'][:2])
        
        if product.get('business_factors'):
            factors.extend(product['business_factors'][:2])
        
        # عوامل پایه
        price = metadata.get('price_numeric', 0)
        if price < 5000000:
            factors.append("قیمت مناسب")
        
        brand = metadata.get('brand', '')
        if brand.lower() in ['yamaha', 'honda', 'suzuki', 'mt', 'smk']:
            factors.append("برند معتبر")
        
        return " | ".join(factors[:3]) if factors else "امتیاز بالا"

    def _generate_alternative_reason(
        self, 
        alternative: Dict[str, Any], 
        best_choice: Dict[str, Any]
    ) -> str:
        """تولید دلیل پیشنهاد جایگزین"""
        alt_metadata = alternative.get('metadata', {})
        best_metadata = best_choice.get('metadata', {})
        
        alt_price = alt_metadata.get('price_numeric', 0)
        best_price = best_metadata.get('price_numeric', 0)
        
        if alt_price < best_price * 0.8:
            return "گزینه اقتصادی‌تر"
        elif alt_price > best_price * 1.2:
            return "کیفیت بالاتر"
        else:
            return "ویژگی‌های متفاوت"

    async def _make_recommendations(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 5: تولید توصیه‌ها"""
        
        analysis = context.intermediate_results.get('analyze_options', {})
        search_results = context.intermediate_results.get('search_and_filter', [])
        
        if not search_results:
            return {
                'primary_recommendation': None,
                'alternatives': [],
                'reasoning': 'هیچ محصول مناسبی یافت نشد'
            }
        
        recommendations = {
            'primary_recommendation': None,
            'alternatives': [],
            'reasoning': '',
            'confidence': 0.0,
            'next_steps': []
        }
        
        # توصیه اصلی بر اساس تحلیل
        if analysis.get('analysis_type') == 'comparative':
            best_choice = analysis.get('top_choice')
            if best_choice:
                recommendations['primary_recommendation'] = self._find_product_by_name(
                    search_results, best_choice
                )
                recommendations['reasoning'] = f"بر اساس مقایسه تخصصی، {best_choice} بهترین انتخاب است"
                recommendations['confidence'] = 0.9
        
        elif analysis.get('analysis_type') == 'simple':
            best_choice = analysis.get('best_choice')
            if best_choice:
                recommendations['primary_recommendation'] = self._find_product_by_name(
                    search_results, best_choice
                )
                recommendations['reasoning'] = f"بر اساس معیارهای شما، {best_choice} مناسب‌ترین گزینه است"
                recommendations['confidence'] = 0.7
        
        # گزینه‌های جایگزین
        if len(search_results) > 1:
            remaining_products = [
                p for p in search_results[:5] 
                if p != recommendations['primary_recommendation']
            ]
            recommendations['alternatives'] = remaining_products[:3]
        
        # تعیین قدم‌های بعدی
        recommendations['next_steps'] = self._generate_next_steps(context, recommendations)
        
        return recommendations

    def _find_product_by_name(self, products: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """پیدا کردن محصول بر اساس نام"""
        for product in products:
            if product.get('metadata', {}).get('name', '') == name:
                return product
        return products[0] if products else None

    def _generate_next_steps(
        self, 
        context: ReasoningContext, 
        recommendations: Dict[str, Any]
    ) -> List[str]:
        """تولید قدم‌های بعدی"""
        steps = []
        
        need_analysis = context.intermediate_results.get('understand_need', {})
        
        # اگر intent خرید دارد
        if need_analysis.get('purchase_intent'):
            steps.append("بررسی موجودی و سفارش")
            steps.append("انتخاب سایز مناسب")
        else:
            steps.append("مقایسه با سایر گزینه‌ها")
            steps.append("مشورت با متخصص")
        
        # اگر محصولات مکمل نیاز دارد
        primary_rec = recommendations.get('primary_recommendation')
        if primary_rec:
            category = primary_rec.get('metadata', {}).get('category', '')
            if category in ['کلاه کاسکت', 'پوشاک موتورسواری']:
                steps.append("بررسی محصولات مکمل")
        
        return steps

    async def _suggest_complementary(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 6: پیشنهاد محصولات مکمل"""
        
        recommendations = context.intermediate_results.get('make_recommendations', {})
        primary_rec = recommendations.get('primary_recommendation')
        
        if not primary_rec:
            return {'complementary_products': [], 'reasoning': 'محصول اصلی یافت نشد'}
        
        # تشخیص دسته محصول اصلی
        main_category = primary_rec.get('metadata', {}).get('category', '')
        
        # استفاده از ابزار cross-sell
        cross_sell_tool = CrossSellTool(
            main_product_category=main_category,
            budget_remaining=self._calculate_remaining_budget(context, primary_rec),
            customer_type=context.user_profile.customer_type if context.user_profile else "general"
        )
        
        try:
            cross_sell_result = await cross_sell_tool(rdb)
            cross_sell_data = json.loads(cross_sell_result)
            
            return {
                'complementary_products': cross_sell_data.get('recommendations', []),
                'priority_items': cross_sell_data.get('priority_items', []),
                'optional_items': cross_sell_data.get('optional_items', []),
                'total_value': cross_sell_data.get('total_suggested_value', 0),
                'reasoning': f"محصولات مکمل برای {main_category}"
            }
            
        except Exception as e:
            context.warnings.append(f"خطا در پیشنهاد محصولات مکمل: {str(e)}")
            return {'complementary_products': [], 'reasoning': 'خطا در تولید پیشنهادات'}

    def _calculate_remaining_budget(
        self, 
        context: ReasoningContext, 
        primary_product: Dict[str, Any]
    ) -> Optional[float]:
        """محاسبه بودجه باقیمانده"""
        
        need_analysis = context.intermediate_results.get('understand_need', {})
        budget_constraint = need_analysis.get('budget_constraint')
        
        if not budget_constraint:
            return None
        
        max_budget = budget_constraint.get('max', 0)
        primary_price = primary_product.get('metadata', {}).get('price_numeric', 0)
        
        remaining = max_budget - primary_price
        return remaining if remaining > 0 else None

    async def _provide_guidance(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 7: ارائه راهنمایی"""
        
        guidance = {
            'installation_tips': [],
            'maintenance_advice': [],
            'safety_warnings': [],
            'usage_recommendations': [],
            'warranty_info': []
        }
        
        recommendations = context.intermediate_results.get('make_recommendations', {})
        primary_rec = recommendations.get('primary_recommendation')
        
        if primary_rec:
            category = primary_rec.get('metadata', {}).get('category', '')
            
            # راهنمایی بر اساس دسته محصول
            if 'کلاه کاسکت' in category:
                guidance['installation_tips'].append("سایز کلاه باید دقیقاً مناسب سر باشد")
                guidance['safety_warnings'].append("حتماً استاندارد DOT یا ECE داشته باشد")
                guidance['maintenance_advice'].append("هر 5 سال کلاه را تعویض کنید")
                
            elif 'لاستیک' in category:
                guidance['installation_tips'].append("نصب توسط متخصص انجام شود")
                guidance['safety_warnings'].append("فشار باد را منظماً چک کنید")
                guidance['maintenance_advice'].append("هر 6 ماه چرخش لاستیک انجام دهید")
                
            elif 'دستکش' in category:
                guidance['installation_tips'].append("سایز دقیق انگشتان مهم است")
                guidance['usage_recommendations'].append("برای شستشو از آب ولرم استفاده کنید")
        
        # راهنمایی عمومی بر اساس پروفایل کاربر
        if context.user_profile:
            if context.user_profile.technical_expertise == 'beginner':
                guidance['usage_recommendations'].append("مطالعه دفترچه راهنما ضروری است")
                guidance['installation_tips'].append("در صورت عدم اطمینان از متخصص کمک بگیرید")
        
        return guidance

    async def _validate_results(self, context: ReasoningContext, rdb) -> Dict[str, Any]:
        """مرحله 8: اعتبارسنجی نتایج"""
        
        validation = {
            'overall_confidence': 0.0,
            'validation_checks': [],
            'potential_issues': [],
            'quality_score': 0.0,
            'completeness_score': 0.0
        }
        
        # بررسی کیفیت توصیه‌ها
        recommendations = context.intermediate_results.get('make_recommendations', {})
        
        if recommendations.get('primary_recommendation'):
            validation['validation_checks'].append("✅ توصیه اصلی موجود")
            validation['completeness_score'] += 0.4
        else:
            validation['potential_issues'].append("❌ توصیه اصلی یافت نشد")
        
        if recommendations.get('alternatives'):
            validation['validation_checks'].append("✅ گزینه‌های جایگزین موجود")
            validation['completeness_score'] += 0.2
        
        # بررسی سازگاری (اگر مدل موتور مشخص است)
        need_analysis = context.intermediate_results.get('understand_need', {})
        motorcycle_model = need_analysis.get('motorcycle_model')
        
        if motorcycle_model and recommendations.get('primary_recommendation'):
            # بررسی سازگاری
            compatibility_tool = CompatibilityCheckTool(
                motorcycle_model=motorcycle_model,
                target_products=[recommendations['primary_recommendation'].get('metadata', {}).get('name', '')]
            )
            
            try:
                compatibility_result = await compatibility_tool(rdb)
                compatibility_data = json.loads(compatibility_result)
                
                overall_compatibility = compatibility_data.get('overall_compatibility', 'unknown')
                if overall_compatibility in ['highly_compatible', 'mostly_compatible']:
                    validation['validation_checks'].append("✅ سازگاری با موتور تأیید شد")
                    validation['quality_score'] += 0.3
                else:
                    validation['potential_issues'].append("⚠️ نیاز به بررسی سازگاری")
                    
            except Exception as e:
                validation['potential_issues'].append("❌ خطا در بررسی سازگاری")
        
        # بررسی کامل بودن اطلاعات
        if context.intermediate_results.get('suggest_complementary'):
            validation['validation_checks'].append("✅ محصولات مکمل پیشنهاد شد")
            validation['completeness_score'] += 0.2
        
        if context.intermediate_results.get('provide_guidance'):
            validation['validation_checks'].append("✅ راهنمایی ارائه شد")
            validation['completeness_score'] += 0.2
        
        # محاسبه اعتماد کلی
        step_confidences = list(context.confidence_scores.values())
        if step_confidences:
            avg_confidence = sum(step_confidences) / len(step_confidences)
            validation['overall_confidence'] = (avg_confidence + validation['quality_score'] + validation['completeness_score']) / 3
        
        return validation

    def _calculate_step_confidence(
        self, 
        step: ReasoningStep, 
        result: Any, 
        context: ReasoningContext
    ) -> float:
        """محاسبه اعتماد برای هر مرحله"""
        
        if step == ReasoningStep.UNDERSTAND_NEED:
            # اعتماد بر اساس تشخیص نوع محصول
            if result.get('primary_need') and result['primary_need'] != 'نامشخص':
                return 0.9
            else:
                return 0.5
                
        elif step == ReasoningStep.SEARCH_AND_FILTER:
            # اعتماد بر اساس تعداد نتایج
            if isinstance(result, list):
                if len(result) >= 5:
                    return 0.9
                elif len(result) >= 2:
                    return 0.7
                elif len(result) >= 1:
                    return 0.5
                else:
                    return 0.1
            return 0.1
            
        elif step == ReasoningStep.ANALYZE_OPTIONS:
            # اعتماد بر اساس نوع تحلیل
            if result.get('analysis_type') == 'comparative':
                return 0.9
            elif result.get('analysis_type') == 'simple':
                return 0.7
            else:
                return 0.3
                
        elif step == ReasoningStep.MAKE_RECOMMENDATIONS:
            # اعتماد بر اساس وجود توصیه اصلی
            if result.get('primary_recommendation'):
                return result.get('confidence', 0.7)
            else:
                return 0.2
        
        # پیش‌فرض برای سایر مراحل
        return 0.8

    def _generate_final_result(self, context: ReasoningContext) -> Dict[str, Any]:
        """تولید نتیجه نهایی"""
        
        return {
            'original_query': context.original_query,
            'processing_steps': [step.value for step in context.steps_completed],
            'results': {
                'need_analysis': context.intermediate_results.get('understand_need', {}),
                'search_results': len(context.intermediate_results.get('search_and_filter', [])),
                'recommendations': context.intermediate_results.get('make_recommendations', {}),
                'complementary_products': context.intermediate_results.get('suggest_complementary', {}),
                'guidance': context.intermediate_results.get('provide_guidance', {}),
                'validation': context.intermediate_results.get('validate_results', {})
            },
            'confidence_scores': context.confidence_scores,
            'warnings': context.warnings,
            'reasoning_log': context.reasoning_log,
            'summary': self._generate_summary(context)
        }

    def _generate_summary(self, context: ReasoningContext) -> Dict[str, Any]:
        """تولید خلاصه نتایج"""
        
        recommendations = context.intermediate_results.get('make_recommendations', {})
        validation = context.intermediate_results.get('validate_results', {})
        
        return {
            'success': len(context.steps_completed) >= 3,
            'primary_recommendation': recommendations.get('primary_recommendation', {}).get('metadata', {}).get('name'),
            'overall_confidence': validation.get('overall_confidence', 0.0),
            'steps_completed': len(context.steps_completed),
            'issues_found': len(context.warnings),
            'recommendation_quality': 'high' if validation.get('overall_confidence', 0) > 0.7 else 'medium' if validation.get('overall_confidence', 0) > 0.5 else 'low'
        }

