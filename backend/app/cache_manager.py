import json
import hashlib
import time
from typing import Any, Optional, List, Dict
from redis.asyncio import Redis
from app.config import settings

class CacheManager:
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 1 ساعت

    async def get_redis(self):
        if self.redis_client is None:
            self.redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=False
            )
        return self.redis_client

    def generate_key(self, prefix: str, query: str, params: Dict = None) -> str:
        """ایجاد کلید منحصر به فرد برای کش"""
        data = {"query": query, "params": params or {}}
        serialized = json.dumps(data, sort_keys=True)
        hash_key = hashlib.md5(serialized.encode()).hexdigest()
        return f"{prefix}:{hash_key}"

    async def get(self, key: str) -> Optional[Any]:
        """دریافت داده از کش"""
        rdb = await self.get_redis()
        cached = await rdb.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """ذخیره داده در کش"""
        rdb = await self.get_redis()
        await rdb.set(key, json.dumps(value), ex=ttl or self.default_ttl)

    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """دریافت چندین مقدار از کش به صورت همزمان"""
        rdb = await self.get_redis()
        values = await rdb.mget(keys)
        return {key: json.loads(val) if val else None for key, val in zip(keys, values)}

    async def set_multi(self, data: Dict[str, Any], ttl: int = None) -> None:
        """ذخیره چندین مقدار در کش به صورت همزمان"""
        rdb = await self.get_redis()
        pipe = rdb.pipeline()
        for key, value in data.items():
            pipe.set(key, json.dumps(value), ex=ttl or self.default_ttl)
        await pipe.execute()

    async def flush_all(self):
        """پاک کردن تمام کش"""
        rdb = await self.get_redis()
        await rdb.flushdb()
        await rdb.close()
        self.redis_client = None

cache_manager = CacheManager()