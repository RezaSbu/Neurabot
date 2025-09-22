from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.config import settings
from app.redis_client import get_redis
from app.postgres import get_pg_pool, setup_postgres, sync_chats_forever
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NeuraQueen API", description="API for NeuraQueen Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تغییر مسیر API برای حل مشکل 404
app.include_router(router)  # حذف prefix="/api"

@app.head("/health")
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_tasks():
    logger.info("Starting up NeuraQueen API...")
    
    rdb = get_redis()
    try:
        await rdb.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    async def try_sync():
        try:
            # اطمینان از ایجاد اندیس‌ها قبل از شروع همگام‌سازی
            from app.db import setup_db, create_chat_index
            await setup_db(rdb)
            await create_chat_index(rdb)
            logger.info("Database indices created successfully")
            
            pg_pool = await get_pg_pool()
            await setup_postgres(pg_pool)
            # ایجاد تسک بدون await برای جلوگیری از خطا
            task = asyncio.create_task(sync_chats_forever(rdb, pg_pool))
            logger.info("[SYNC] Background sync to PostgreSQL started ✅")
        except Exception as e:
            logger.warning(f"[SYNC WARNING] PostgreSQL not available, sync skipped: {e}")
    
    # ایجاد تسک بدون await برای جلوگیری از خطا
    asyncio.create_task(try_sync())
    logger.info("NeuraQueen API startup completed")

@app.get("/")
async def root():
    return {"message": "NeuraQueen API is running", "version": "1.9"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)