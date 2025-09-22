import asyncpg
import re
import asyncio
from app.config import settings
from app.db import get_all_chats
from app.redis_client import get_redis
import logging

logger = logging.getLogger(__name__)

# اتصال به PostgreSQL
async def get_pg_pool():
    try:
        return await asyncpg.create_pool(dsn=settings.POSTGRES_DSN)
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None

# ساخت جداول در صورت نیاز
async def setup_postgres(pool):
    if pool is None:
        logger.warning("PostgreSQL pool is None, skipping setup")
        return
        
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    ip TEXT,
                    email TEXT,
                    created BIGINT
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    created BIGINT,
                    session_id TEXT REFERENCES sessions(session_id)
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    chat_id TEXT REFERENCES chats(id),
                    role TEXT,
                    content TEXT,
                    created BIGINT
                );
            """)
            logger.info("PostgreSQL tables created successfully")
        except Exception as e:
            logger.error(f"Error setting up PostgreSQL tables: {e}")

# استخراج session_id و chat_id از کلیدهای Redis
def extract_session_data(keys):
    pattern = re.compile(r"session:(.*?):chat:(.*?)$")
    return [
        (match.group(1), match.group(2))
        for key in keys
        if (match := pattern.match(key.decode() if isinstance(key, bytes) else key))
    ]

# اجرای sync دائمی Redis → PostgreSQL
async def sync_chats_forever(redis, pg_pool):
    if pg_pool is None:
        logger.warning("PostgreSQL pool is None, skipping sync")
        return
        
    while True:
        try:
            keys = await redis.keys("session:*:chat:*")
            session_chat_pairs = extract_session_data(keys)
            chats = await get_all_chats(redis)

            if not chats:
                logger.info("No chats to sync")
                await asyncio.sleep(30)
                continue

            async with pg_pool.acquire() as conn:
                for chat in chats:
                    chat_id = chat["id"]
                    created = chat.get("created", 0)

                    # گرفتن session_id برای هر chat_id
                    session_id = None
                    for sid, cid in session_chat_pairs:
                        if cid == chat_id:
                            session_id = sid
                            break

                    # ذخیره session (اگر session_id داشت)
                    if session_id:
                        ip = await redis.get(f"session:{session_id}:ip")
                        email = await redis.get(f"session:{session_id}:email")
                        await conn.execute("""
                            INSERT INTO sessions (session_id, ip, email, created)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (session_id) DO NOTHING
                        """,
                        session_id,
                        ip.decode() if ip else None,
                        email.decode() if email else None,
                        created)

                    # ذخیره chat
                    await conn.execute("""
                        INSERT INTO chats (id, created, session_id)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) DO NOTHING
                    """, chat_id, created, session_id)

                    # ذخیره فقط پیام‌های جدید
                    for msg in chat.get("messages", []):
                        exists = await conn.fetchval("""
                            SELECT 1 FROM messages
                            WHERE chat_id = $1 AND role = $2 AND content = $3 AND created = $4
                            LIMIT 1
                        """, chat_id, msg["role"], msg["content"], msg.get("created", 0))

                        if exists:
                            continue  # پیام تکراری، ذخیره نکن

                        await conn.execute("""
                            INSERT INTO messages (chat_id, role, content, created)
                            VALUES ($1, $2, $3, $4)
                        """, chat_id, msg["role"], msg["content"], msg.get("created", 0))

            logger.info(f"[SYNC] ✅ Synced {len(chats)} chats")

        except Exception as e:
            logger.error(f"[SYNC ERROR] {e}")

        await asyncio.sleep(30)  # کاهش فاصله همگام‌سازی به 30 ثانیه