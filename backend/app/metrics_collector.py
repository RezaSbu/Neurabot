import time
from typing import Dict, Any, List
from app.db import get_redis

class MetricsCollector:
    def __init__(self):
        self.redis_client = None

    async def get_redis(self):
        if self.redis_client is None:
            self.redis_client = get_redis()
        return self.redis_client

    async def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """ثبت معیار عملکردی"""
        rdb = await self.get_redis()
        timestamp = int(time.time())
        key = f"metric:{metric_name}:{timestamp}"
        data = {
            "value": value,
            "tags": tags or {},
            "timestamp": timestamp
        }
        await rdb.set(key, data)
        # تنظیم TTL برای داده‌های قدیمی
        await rdb.expire(key, 604800)  # 7 روز

    async def record_query_performance(self, query: str, retrieval_time: float, generation_time: float, total_time: float, model_used: str):
        """ثبت معیارهای عملکرد کوئری"""
        await self.record_metric("query_performance", total_time, {"query": query[:50]})
        await self.record_metric("retrieval_time", retrieval_time)
        await self.record_metric("generation_time", generation_time)
        await self.record_metric("model_usage", 1, {"model": model_used})

    async def record_user_feedback(self, chat_id: str, message_id: str, feedback: str, comment: str = None):
        """ثبت بازخورد کاربر"""
        await self.record_metric("user_feedback", 1, {"type": feedback, "chat_id": chat_id, "message_id": message_id})
        
        # ذخیره بازخورد با جزئیات بیشتر
        rdb = await self.get_redis()
        feedback_key = f"feedback:{chat_id}:{message_id}"
        await rdb.set(feedback_key, {
            "feedback": feedback,
            "comment": comment,
            "timestamp": int(time.time())
        })
        await rdb.expire(feedback_key, 2592000)  # 30 روز

    async def get_metrics(self, metric_name: str, time_range: int = 86400) -> List[Dict]:
        """دریافت معیارهای عملکردی در یک بازه زمانی"""
        rdb = await self.get_redis()
        current_time = int(time.time())
        start_time = current_time - time_range
        
        keys = await rdb.keys(f"metric:{metric_name}:*")
        metrics = []
        
        for key in keys:
            timestamp = int(key.split(":")[-1])
            if start_time <= timestamp <= current_time:
                data = await rdb.get(key)
                if data:
                    metrics.append(data)
        
        return metrics

metrics_collector = MetricsCollector()