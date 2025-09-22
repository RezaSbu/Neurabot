import re
from typing import List, Dict, Any, Optional
from app.model_manager import model_manager
from app.cache_manager import cache_manager

class QueryProcessor:
    def __init__(self):
        self.cache = cache_manager

    async def transform_query(self, original_query: str, context: str = "") -> List[str]:
        """بازنویسی و گسترش کوئری برای بهبود بازیابی"""
        cache_key = self.cache.generate_key("query_transform", original_query)
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        prompt = f"""
        برای بهبود جستجو در پایگاه داده محصولات موتورسیکلت، کوئری کاربر را به 3-5 کوئری مرتبط بازنویسی و گسترش دهید.
        کوئری اصلی: {original_query}
        زمینه اضافی: {context}
        
        فقط کوئری‌های بازنویسی شده را به صورت یک لیست JSON برگردانید.
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = ""
        
        async for event in await model_manager.chat_completion(messages):
            if event.type == 'content.delta':
                response += event.delta
        
        try:
            # استخراج لیست JSON از پاسخ
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                transformed_queries = json.loads(json_match.group())
                # اطمینان از اینکه کوئری اصلی همیشه در نتایج وجود دارد
                if original_query not in transformed_queries:
                    transformed_queries.insert(0, original_query)
                
                await self.cache.set(cache_key, transformed_queries)
                return transformed_queries
        except Exception as e:
            print(f"Error parsing transformed queries: {e}")
        
        return [original_query]

    async def decompose_query(self, query: str) -> List[str]:
        """تجزیه سوالات پیچیده به زیرسوالات ساده‌تر"""
        cache_key = self.cache.generate_key("query_decompose", query)
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        prompt = f"""
        سوال پیچیده زیر را به 2-3 سوال ساده‌تر تجزیه کن که هر کدام به تنهایی قابل پاسخگویی باشند.
        سوال اصلی: {query}
        
        فقط سوالات تجزیه شده را به صورت یک لیست JSON برگردانید.
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = ""
        
        async for event in await model_manager.chat_completion(messages):
            if event.type == 'content.delta':
                response += event.delta
        
        try:
            # استخراج لیست JSON از پاسخ
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                sub_queries = json.loads(json_match.group())
                # اطمینان از اینکه کوئری اصلی همیشه در نتایج وجود دارد
                if query not in sub_queries:
                    sub_queries.insert(0, query)
                
                await self.cache.set(cache_key, sub_queries)
                return sub_queries
        except Exception as e:
            print(f"Error parsing decomposed queries: {e}")
        
        return [query]

    async def process_query(self, query: str, context: str = "") -> Dict[str, Any]:
        """پردازش کامل کوئری شامل تبدیل و تجزیه"""
        # Query Transformation
        transformed_queries = await self.transform_query(query, context)
        
        # Multi-Step Retrieval: اگر کوئری پیچیده است، آن را تجزیه می‌کنیم
        sub_queries = []
        for t_query in transformed_queries:
            sub_queries.extend(await self.decompose_query(t_query))
        
        result = {
            "original_query": query,
            "transformed_queries": transformed_queries,
            "sub_queries": sub_queries
        }
        
        return result

query_processor = QueryProcessor()