import asyncpg
import re
from app.config import settings
from app.db import get_all_chats

# اتصال به PostgreSQL
async def get_pg_pool():
    return await asyncpg.create_pool(dsn=settings.POSTGRES_DSN)

# ساخت جداول
async def setup_postgres(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                ip TEXT,
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

# استخراج session_id و chat_id از Redis keys
def extract_session_data(keys):
    pattern = re.compile(r"session:(.*?):chat:(.*?)$")
    return [
        (match.group(1), match.group(2))
        for key in keys
        if (match := pattern.match(key.decode() if isinstance(key, bytes) else key))
    ]

# اجرای بلادرنگ سینک Redis → PostgreSQL
async def sync_chats_forever(redis, pg_pool):
    synced_chats = set()

    while True:
        try:
            keys = await redis.keys("session:*:chat:*")
            session_chat_pairs = extract_session_data(keys)
            chats = await get_all_chats(redis)

            async with pg_pool.acquire() as conn:
                for chat in chats:
                    chat_id = chat["id"]
                    if chat_id in synced_chats:
                        continue

                    created = chat.get("created", 0)
                    session_id = None
                    for sid, cid in session_chat_pairs:
                        if cid == chat_id:
                            session_id = sid
                            break

                    # ذخیره session
                    if session_id:
                        ip = await redis.get(f"session:{session_id}:ip")
                        await conn.execute("""
                            INSERT INTO sessions (session_id, ip, created)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (session_id) DO NOTHING
                        """, session_id, ip.decode() if ip else None, created)

                    # ذخیره chat
                    await conn.execute("""
                        INSERT INTO chats (id, created, session_id)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) DO NOTHING
                    """, chat_id, created, session_id)

                    # ذخیره پیام‌ها
                    for msg in chat.get("messages", []):
                        await conn.execute("""
                            INSERT INTO messages (chat_id, role, content, created)
                            VALUES ($1, $2, $3, $4)
                        """, chat_id, msg["role"], msg["content"], msg.get("created", 0))

                    synced_chats.add(chat_id)

            print(f"[SYNC] ✅ Synced {len(synced_chats)} chats")

        except Exception as e:
            print(f"[SYNC ERROR] {e}")

        from asyncio import sleep
        await sleep(5)
