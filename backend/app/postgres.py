import asyncpg
import re
from app.config import settings
from app.db import get_all_chats

# اتصال به PostgreSQL
async def get_pg_pool():
    return await asyncpg.create_pool(dsn=settings.POSTGRES_DSN)

# ساخت جداول در صورت نیاز
async def setup_postgres(pool):
    async with pool.acquire() as conn:
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
    while True:
        try:
            keys = await redis.keys("session:*:chat:*")
            session_chat_pairs = extract_session_data(keys)
            chats = await get_all_chats(redis)

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

            print(f"[SYNC] ✅ Synced {len(chats)} chats")

        except Exception as e:
            print(f"[SYNC ERROR] {e}")

        from asyncio import sleep
        await sleep(5)
