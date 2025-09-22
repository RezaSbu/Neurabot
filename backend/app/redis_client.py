from redis.asyncio import Redis
from app.config import settings

def get_redis():
    """دریافت اتصال Redis"""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=False
    )