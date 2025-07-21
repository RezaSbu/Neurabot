from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.config import settings
from app.db import get_redis
from app.postgres import get_pg_pool, setup_postgres, sync_chats_forever  # منتقل شده به postgres.py
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.head("/health")
@app.get("/health")
def health_check():
    return "ok"

@app.on_event("startup")
async def startup_tasks():
    redis = get_redis()

    async def try_sync():
        try:
            pg_pool = await get_pg_pool()
            await setup_postgres(pg_pool)
            asyncio.create_task(sync_chats_forever(redis, pg_pool))  # 🎯 مستقل، پس زمینه
            print("[SYNC] Background sync to PostgreSQL started ✅")
        except Exception as e:
            print(f"[SYNC WARNING] PostgreSQL not available, sync skipped: {e}")

    asyncio.create_task(try_sync())  # ✨ حتی اگر شکست خورد، مانع اجرا نمی‌شه
