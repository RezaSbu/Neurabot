import re
from typing import Dict, Any
from app.model_manager import model_manager

class ResponseReflector:
    def __init__(self):
        pass

    async def reflect(self, query: str, response: str, context: str, sources: list = None) -> str:
        """بازبینی و اصلاح پاسخ‌های تولید شده"""
        prompt = f"""
        با توجه به سوال کاربر، زمینه ارائه شده و منابع اطلاعاتی، پاسخ زیر را بررسی کن.
        اگر پاسخ ناقص، نادرست یا نیاز به بهبود دارد، آن را اصلاح کن.
        در غیر این صورت، همان پاسخ را بازگردان.
        
        سوال: {query}
        زمینه: {context}
        منابع: {sources if sources else 'مشخص نشده'}
        پاسخ اولیه: {response}
        
        پاسخ نهایی:
        """
        
        messages = [{"role": "user", "content": prompt}]
        refined_response = ""
        
        async for event in await model_manager.chat_completion(messages):
            if event.type == 'content.delta':
                refined_response += event.delta
        
        return refined_response

    async def extract_citations(self, response: str, sources: list) -> str:
        """استخراج و افزودن استنادها به پاسخ"""
        if not sources:
            return response
        
        # در اینجا می‌توان الگوریتم‌های پیچیده‌تری برای استخراج استنادها پیاده‌سازی کرد
        # برای سادگی، ما فقط منابع را به انتهای پاسخ اضافه می‌کنیم
        citations = "\n\nمنابع:\n"
        for i, source in enumerate(sources[:5], 1):  # حداکثر ۵ منبع
            citations += f"{i}. {source.get('title', 'بدون عنوان')} - {source.get('url', '#')}\n"
        
        return response + citations

response_reflector = ResponseReflector()