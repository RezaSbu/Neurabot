from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime
from time import time

from app.assistants.prompts import EXPERT_ADMIN_PROMPT, EXPERT_SYSTEM_PROMPT, EXPERT_RAG_SYSTEM_PROMPT
from app.openai import chat_stream
from app.db import get_chat_messages, add_chat_messages
from app.assistants.tools import QueryKnowledgeBaseTool
from app.assistants.advanced_tools import (
    ProductComparisonTool,
    CompatibilityCheckTool, 
    CrossSellTool,
    StockAnalyticsTool
)
from app.memory.customer_profile import CustomerProfile
from app.intelligence.business_logic import BusinessIntelligence
from app.search.enhanced_search import EnhancedSearchEngine
from app.reasoning.chain_of_thought import ReasoningChain
from app.response.formatter import ResponseFormatter
from app.utils.sse_stream import SSEStream
from app.config import settings

from openai import pydantic_function_tool

class ExpertRAGAssistant:
    """دستیار متخصص RAG با قابلیت‌های پیشرفته سطح ادمین حرفه‌ای"""
    
    def __init__(self, chat_id: str, rdb, session_id: str = None):
        self.chat_id = chat_id
        self.rdb = rdb
        self.session_id = session_id
        self.sse_stream = None
        
        # Core components
        self.business_intelligence = BusinessIntelligence()
        self.enhanced_search = EnhancedSearchEngine()
        self.reasoning_chain = ReasoningChain()
        self.response_formatter = ResponseFormatter()
        
        # Customer profiling
        self.customer_profile: Optional[CustomerProfile] = None
        
        # System messages
        self.expert_system_message = {'role': 'system', 'content': EXPERT_SYSTEM_PROMPT}
        self.expert_rag_message = {'role': 'system', 'content': EXPERT_RAG_SYSTEM_PROMPT}
        
        # Advanced tools
        self.advanced_tools_schema = [
            pydantic_function_tool(QueryKnowledgeBaseTool),
            pydantic_function_tool(ProductComparisonTool),
            pydantic_function_tool(CompatibilityCheckTool),
            pydantic_function_tool(CrossSellTool),
            pydantic_function_tool(StockAnalyticsTool)
        ]
        
        # Configuration
        self.max_tool_calls = settings.MAX_TOOL_CALLS
        self.history_size = settings.HISTORY_SIZE
        
        # Performance tracking
        self.performance_metrics = {
            'total_queries': 0,
            'successful_responses': 0,
            'average_response_time': 0.0,
            'tool_usage_stats': {},
            'customer_satisfaction_indicators': []
        }

    async def run(self, message: str) -> SSEStream:
        """اجرای دستیار متخصص با پردازش پیشرفته"""
        
        self.sse_stream = SSEStream()
        
        # شروع پردازش در background
        asyncio.create_task(self._expert_process_message(message))
        
        return self.sse_stream

    async def _expert_process_message(self, message: str) -> None:
        """پردازش پیشرفته پیام با تمام قابلیت‌های متخصص"""
        
        start_time = time()
        
        try:
            # مرحله 1: بارگذاری پروفایل مشتری
            await self._load_customer_profile()
            
            # مرحله 2: تحلیل عمیق intent
            intent_analysis = await self._deep_intent_analysis(message)
            
            # مرحله 3: پردازش با زنجیره استدلال
            reasoning_result = await self._process_with_reasoning_chain(message, intent_analysis)
            
            # مرحله 4: تولید پاسخ متخصص
            expert_response = await self._generate_expert_response(
                message, intent_analysis, reasoning_result
            )
            
            # مرحله 5: ارسال پاسخ نهایی
            await self._send_expert_response(expert_response)
            
            # مرحله 6: به‌روزرسانی پروفایل مشتری
            await self._update_customer_profile(message, expert_response)
            
            # مرحله 7: ذخیره در تاریخچه
            await self._save_conversation_history(message, expert_response['content'])
            
            # به‌روزرسانی متریک‌ها
            self._update_performance_metrics(True, time() - start_time)
            
        except Exception as e:
            error_message = f"❌ متأسفانه مشکلی پیش آمد. لطفاً دوباره تلاش کنید.\n\n**جزئیات خطا برای پشتیبانی:** {str(e)}"
            await self.sse_stream.send(error_message)
            
            # به‌روزرسانی متریک‌ها
            self._update_performance_metrics(False, time() - start_time)
            
        finally:
            await self.sse_stream.close()

    async def _load_customer_profile(self) -> None:
        """بارگذاری پروفایل مشتری"""
        
        if self.session_id:
            try:
                self.customer_profile = await CustomerProfile.load_from_redis(
                    self.session_id, self.rdb
                )
                
                if not self.customer_profile:
                    # ایجاد پروفایل جدید
                    self.customer_profile = CustomerProfile(session_id=self.session_id)
                    
            except Exception as e:
                print(f"Error loading customer profile: {e}")
                self.customer_profile = CustomerProfile(session_id=self.session_id or "default")

    async def _deep_intent_analysis(self, message: str) -> Dict[str, Any]:
        """تحلیل عمیق intent با استفاده از هوش تجاری"""
        
        # گرفتن تاریخچه مکالمه
        conversation_history = await get_chat_messages(
            self.rdb, self.chat_id, last_n=5
        )
        
        context = {
            'conversation_history': conversation_history,
            'customer_profile': self.customer_profile,
            'current_time': datetime.now().isoformat(),
            'session_id': self.session_id
        }
        
        # تحلیل intent با business intelligence
        intent_analysis = await self.business_intelligence.analyze_query_intent(
            message, context, self.customer_profile
        )
        
        return intent_analysis

    async def _process_with_reasoning_chain(
        self, 
        message: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """پردازش با زنجیره استدلال چندمرحله‌ای"""
        
        # اگر query پیچیده است، از reasoning chain استفاده کن
        complexity_indicators = [
            'مقایسه', 'بهتر', 'تفاوت', 'چرا', 'چطور', 
            'کدام', 'یا', 'در مقابل', 'pros and cons'
        ]
        
        is_complex = (
            any(indicator in message.lower() for indicator in complexity_indicators) or
            intent_analysis.get('confidence', 0) < 0.7 or
            len(message.split()) > 10
        )
        
        if is_complex:
            try:
                reasoning_result = await self.reasoning_chain.process_complex_query(
                    message, self.customer_profile, self.rdb
                )
                return reasoning_result
                
            except Exception as e:
                print(f"Error in reasoning chain: {e}")
                return {'error': str(e), 'fallback': True}
        
        return {'simple_query': True}

    async def _generate_expert_response(
        self, 
        message: str, 
        intent_analysis: Dict[str, Any],
        reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """تولید پاسخ متخصص"""
        
        # اگر نتیجه reasoning chain موجود است، از آن استفاده کن
        if reasoning_result and not reasoning_result.get('simple_query'):
            return await self._format_reasoning_based_response(
                reasoning_result, intent_analysis
            )
        
        # در غیر این صورت، پردازش عادی انجام بده
        return await self._standard_expert_processing(message, intent_analysis)

    async def _format_reasoning_based_response(
        self,
        reasoning_result: Dict[str, Any],
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """فرمت‌بندی پاسخ بر اساس نتیجه reasoning chain"""
        
        # استخراج اطلاعات از reasoning result
        recommendations = reasoning_result.get('results', {}).get('recommendations', {})
        primary_recommendation = recommendations.get('primary_recommendation')
        
        if not primary_recommendation:
            return {
                'content': "متأسفانه نتوانستم محصول مناسبی برای شما پیدا کنم. لطفاً معیارهای خود را دقیق‌تر بیان کنید.",
                'type': 'no_results'
            }
        
        # تولید پاسخ فرمت شده
        products = [primary_recommendation] + recommendations.get('alternatives', [])[:3]
        
        user_context = {
            'intent_analysis': intent_analysis,
            'urgency_level': reasoning_result.get('results', {}).get('need_analysis', {}).get('urgency_level', 'low')
        }
        
        formatted_response = self.response_formatter.format_expert_response(
            products=products,
            analysis=reasoning_result.get('results', {}),
            user_context=user_context,
            reasoning_chain_result=reasoning_result,
            user_profile=self.customer_profile
        )
        
        return {
            'content': formatted_response,
            'type': 'expert_consultation',
            'reasoning_summary': reasoning_result.get('summary', {}),
            'confidence': reasoning_result.get('summary', {}).get('overall_confidence', 0.0)
        }

    async def _standard_expert_processing(
        self, 
        message: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """پردازش استاندارد با ابزارهای پیشرفته"""
        
        # گرفتن تاریخچه مکالمه
        history = await get_chat_messages(self.rdb, self.chat_id, last_n=self.history_size)
        history.append({'role': 'user', 'content': message})
        
        # تعیین استراتژی tool selection
        recommended_approach = intent_analysis.get('recommended_approach', {})
        suggested_tools = recommended_approach.get('tools', ['QueryKnowledgeBaseTool'])
        
        # اجرای مرحله اول: تولید پاسخ اولیه با tool calls
        assistant_msg = await self._generate_chat_response_with_tools(
            system_message=self.expert_system_message,
            chat_messages=history,
            tools=self.advanced_tools_schema,
            tool_choice='auto'
        )
        
        # اجرای tool calls
        tool_results = []
        if hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls:
            tool_results = await self._execute_advanced_tool_calls(
                assistant_msg.tool_calls, history
            )
        
        # تولید پاسخ نهایی با نتایج tools
        if tool_results:
            # اضافه کردن نتایج tools به history
            history.append({
                'role': 'assistant',
                'content': assistant_msg.content or "",
                'tool_calls': assistant_msg.tool_calls
            })
            
            for result in tool_results:
                history.append(result)
            
            # تولید پاسخ نهایی
            final_response = await self._generate_chat_response_with_tools(
                system_message=self.expert_rag_message,
                chat_messages=history
            )
            
            return {
                'content': final_response.content,
                'type': 'tool_based_response',
                'tools_used': [call.function.name for call in assistant_msg.tool_calls],
                'confidence': self._estimate_response_confidence(tool_results)
            }
        
        # اگر tool call نداشتیم، پاسخ مستقیم
        return {
            'content': assistant_msg.content,
            'type': 'direct_response',
            'confidence': 0.7
        }

    async def _execute_advanced_tool_calls(
        self, 
        tool_calls: List, 
        chat_messages: List[Dict]
    ) -> List[Dict[str, Any]]:
        """اجرای tool calls پیشرفته"""
        
        tool_results = []
        executed_count = 0
        
        for call in tool_calls:
            if executed_count >= self.max_tool_calls:
                # اگر به حد tool call رسیدیم
                tool_results.append({
                    'role': 'tool',
                    'tool_call_id': call.id,
                    'content': 'محدودیت تعداد ابزار - این ابزار اجرا نشد'
                })
                continue
            
            try:
                # اجرای tool
                tool_name = call.function.name
                tool_args = call.function.parsed_arguments
                
                # اجرای tool مناسب
                if hasattr(tool_args, '__call__'):
                    result = await tool_args(self.rdb)
                else:
                    result = "خطا در اجرای ابزار"
                
                tool_results.append({
                    'role': 'tool',
                    'tool_call_id': call.id,
                    'content': result
                })
                
                # آمار استفاده از tools
                self.performance_metrics['tool_usage_stats'][tool_name] = \
                    self.performance_metrics['tool_usage_stats'].get(tool_name, 0) + 1
                
                executed_count += 1
                
            except Exception as e:
                tool_results.append({
                    'role': 'tool',
                    'tool_call_id': call.id,
                    'content': f'خطا در اجرای ابزار: {str(e)}'
                })
        
        return tool_results

    async def _generate_chat_response_with_tools(
        self, 
        system_message: Dict[str, str], 
        chat_messages: List[Dict],
        tools: List = None,
        tool_choice: str = None,
        **kwargs
    ) -> Any:
        """تولید پاسخ با قابلیت tool calling"""
        
        messages = [system_message, *chat_messages]
        
        # پارامترهای درخواست
        request_params = {
            'messages': messages,
            'temperature': settings.TEMPERATURE,
            **kwargs
        }
        
        if tools:
            request_params['tools'] = tools
            if tool_choice:
                request_params['tool_choice'] = tool_choice
        
        # اجرای stream
        async with chat_stream(**request_params) as stream:
            # ارسال محتوای streaming به کاربر
            async for event in stream:
                if event.type == 'content.delta':
                    await self.sse_stream.send(event.delta)
            
            # دریافت پاسخ نهایی
            final = await stream.get_final_completion()
            return final.choices[0].message

    async def _send_expert_response(self, response_data: Dict[str, Any]) -> None:
        """ارسال پاسخ متخصص"""
        
        content = response_data.get('content', '')
        response_type = response_data.get('type', 'standard')
        
        # اضافه کردن metadata برای debugging (فقط در development)
        if hasattr(settings, 'DEBUG') and settings.DEBUG:
            metadata = {
                'response_type': response_type,
                'confidence': response_data.get('confidence', 0.0),
                'tools_used': response_data.get('tools_used', [])
            }
            content += f"\n\n<!-- Debug Info: {json.dumps(metadata)} -->"
        
        # ارسال محتوا (اگر از stream استفاده نشده باشد)
        if not hasattr(self, '_content_streamed'):
            await self.sse_stream.send(content)

    async def _update_customer_profile(
        self, 
        user_message: str, 
        response_data: Dict[str, Any]
    ) -> None:
        """به‌روزرسانی پروفایل مشتری"""
        
        if not self.customer_profile:
            return
        
        try:
            # گرفتن تاریخچه اخیر
            recent_messages = await get_chat_messages(self.rdb, self.chat_id, last_n=3)
            recent_messages.append({'role': 'user', 'content': user_message})
            
            # به‌روزرسانی پروفایل
            await self.customer_profile.update_from_conversation(recent_messages, self.rdb)
            
            # اضافه کردن فعالیت مرور
            self.customer_profile.add_browsing_activity({
                'query': user_message,
                'response_type': response_data.get('type', 'standard'),
                'confidence': response_data.get('confidence', 0.0),
                'tools_used': response_data.get('tools_used', [])
            })
            
        except Exception as e:
            print(f"Error updating customer profile: {e}")

    async def _save_conversation_history(
        self, 
        user_message: str, 
        assistant_response: str
    ) -> None:
        """ذخیره تاریخچه مکالمه"""
        
        try:
            messages_to_save = [
                {
                    'role': 'user',
                    'content': user_message,
                    'created': int(time())
                },
                {
                    'role': 'assistant', 
                    'content': assistant_response,
                    'created': int(time()),
                    'metadata': {
                        'assistant_type': 'expert',
                        'processing_time': time() - getattr(self, '_start_time', time())
                    }
                }
            ]
            
            await add_chat_messages(self.rdb, self.chat_id, messages_to_save)
            
        except Exception as e:
            print(f"Error saving conversation history: {e}")

    def _estimate_response_confidence(self, tool_results: List[Dict]) -> float:
        """تخمین اعتماد پاسخ بر اساس نتایج tools"""
        
        if not tool_results:
            return 0.5
        
        # تحلیل کیفیت نتایج tools
        successful_tools = 0
        total_tools = len(tool_results)
        
        for result in tool_results:
            content = result.get('content', '')
            
            # بررسی نشانه‌های موفقیت
            if any(indicator in content for indicator in ['محصول', 'توصیه', 'پیشنهاد']):
                successful_tools += 1
            elif 'خطا' in content or 'یافت نشد' in content:
                successful_tools -= 0.5
        
        # محاسبه اعتماد
        base_confidence = successful_tools / max(total_tools, 1)
        
        # تعدیل بر اساس تعداد tools
        if total_tools >= 3:
            base_confidence += 0.1  # bonus برای استفاده از چندین tool
        
        return max(0.0, min(1.0, base_confidence))

    def _update_performance_metrics(self, success: bool, response_time: float) -> None:
        """به‌روزرسانی متریک‌های عملکرد"""
        
        self.performance_metrics['total_queries'] += 1
        
        if success:
            self.performance_metrics['successful_responses'] += 1
        
        # به‌روزرسانی میانگین زمان پاسخ
        current_avg = self.performance_metrics['average_response_time']
        total_queries = self.performance_metrics['total_queries']
        
        new_avg = ((current_avg * (total_queries - 1)) + response_time) / total_queries
        self.performance_metrics['average_response_time'] = new_avg

    async def get_performance_report(self) -> Dict[str, Any]:
        """گزارش عملکرد دستیار"""
        
        success_rate = 0.0
        if self.performance_metrics['total_queries'] > 0:
            success_rate = (
                self.performance_metrics['successful_responses'] / 
                self.performance_metrics['total_queries']
            ) * 100
        
        return {
            'total_queries': self.performance_metrics['total_queries'],
            'success_rate': round(success_rate, 2),
            'average_response_time': round(self.performance_metrics['average_response_time'], 2),
            'tool_usage_stats': self.performance_metrics['tool_usage_stats'],
            'customer_profile_available': self.customer_profile is not None,
            'advanced_features_active': True
        }

    async def analyze_customer_satisfaction(self) -> Dict[str, Any]:
        """تحلیل رضایت مشتری"""
        
        if not self.customer_profile:
            return {'status': 'no_profile', 'satisfaction': 'unknown'}
        
        # تحلیل الگوهای رفتاری
        browsing_history = self.customer_profile.browsing_history
        
        satisfaction_indicators = {
            'engagement_level': 'medium',
            'query_complexity_trend': 'stable',
            'response_satisfaction': 'unknown',
            'loyalty_indicators': []
        }
        
        # تحلیل سطح تعامل
        if len(browsing_history) > 10:
            satisfaction_indicators['engagement_level'] = 'high'
        elif len(browsing_history) < 3:
            satisfaction_indicators['engagement_level'] = 'low'
        
        # تحلیل نشانه‌های وفاداری
        if self.customer_profile.customer_type in ['loyal', 'returning']:
            satisfaction_indicators['loyalty_indicators'].append('repeat_customer')
        
        if len(self.customer_profile.previous_purchases) > 0:
            satisfaction_indicators['loyalty_indicators'].append('purchase_history')
        
        return satisfaction_indicators

    async def get_personalized_recommendations(self) -> Dict[str, Any]:
        """دریافت توصیه‌های شخصی‌سازی شده"""
        
        if not self.customer_profile:
            return {'recommendations': [], 'message': 'پروفایل مشتری موجود نیست'}
        
        # استفاده از business intelligence برای CLV
        clv_analysis = await self.business_intelligence.predict_customer_lifetime_value(
            self.customer_profile
        )
        
        # ترکیب با توصیه‌های پروفایل
        profile_recommendations = await self.customer_profile.get_personalized_recommendations(self.rdb)
        
        return {
            'profile_recommendations': profile_recommendations,
            'clv_analysis': clv_analysis,
            'personalization_level': 'expert'
        }

