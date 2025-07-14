# Database/backend/admin_api.py

from fastapi import APIRouter, Depends
from app.db import get_redis, get_all_chats
from app.db import CHAT_IDX_PREFIX
from redis.asyncio import Redis

admin_router = APIRouter(tags=["Admin Panel"])

# Dependency: گرفتن اتصال Redis
async def get_rdb():
    rdb = get_redis()
    try:
        yield rdb
    finally:
        await rdb.aclose()

# 📌 گرفتن لیست همه چت‌ها
@admin_router.get("/admin/chats")
async def admin_get_all_chats(rdb: Redis = Depends(get_rdb)):
    return await get_all_chats(rdb)

# 🗑 حذف یک چت با chat_id
@admin_router.delete("/admin/chats/{chat_id}")
async def admin_delete_chat(chat_id: str, rdb: Redis = Depends(get_rdb)):
    await rdb.delete(f"{CHAT_IDX_PREFIX}{chat_id}")
    return {"status": "deleted"}

# 📊 آمار اولیه چت‌ها
@admin_router.get("/admin/stats")
async def admin_chat_stats(rdb: Redis = Depends(get_rdb)):
    chats = await get_all_chats(rdb)
    total = len(chats)
    message_counts = [len(chat.get("messages", [])) for chat in chats]
    avg_len = round(sum(message_counts) / total, 2) if total else 0
    return {
        "total_chats": total,
        "average_messages_per_chat": avg_len
    }
