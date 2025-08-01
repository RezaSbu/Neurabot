from uuid import uuid4
from time import time
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.db import get_redis, create_chat, chat_exists, add_chat_messages
from app.assistants.assistant import RAGAssistant
import re
import dns.resolver  # 🟡 برای بررسی MX Record

class ChatIn(BaseModel):
    message: str

async def get_rdb():
    rdb = get_redis()
    try:
        yield rdb
    finally:
        await rdb.aclose()

# ✅ بررسی MX Record دامنه‌ی ایمیل
def check_email_domain_exists(email: str) -> bool:
    try:
        domain = email.split('@')[1]
        dns.resolver.resolve(domain, 'MX')
        return True
    except Exception:
        return False

router = APIRouter()

@router.post('/chats')
async def create_new_chat(
    request: Request,
    rdb = Depends(get_rdb),
    session_id: str = Header(..., alias='X-Session-ID'),
    email: str = Header(None, alias='X-User-Email')
):
    chat_id = str(uuid4())[:8]
    created = int(time())
    client_ip = request.client.host

    await create_chat(rdb, chat_id, created)
    await rdb.set(f'session:{session_id}:chat:{chat_id}', 1, ex=432000)
    await rdb.set(f'session:{session_id}:ip', client_ip, ex=432000)

    if email:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise HTTPException(status_code=400, detail="فرمت ایمیل وارد شده معتبر نیست.")
        if not check_email_domain_exists(email):
            raise HTTPException(status_code=400, detail="دامنه ایمیل وجود ندارد یا معتبر نیست.")
        await rdb.set(f'session:{session_id}:email', email, ex=432000)
    else:
        existing_email = await rdb.get(f'session:{session_id}:email')
        if existing_email:
            await rdb.set(f'session:{session_id}:email', existing_email.decode(), ex=432000)

    return {'id': chat_id}

@router.post('/chats/{chat_id}')
async def chat(
    chat_id: str,
    chat_in: ChatIn,
    session_id: str = Header(..., alias='X-Session-ID')
):
    rdb = get_redis()

    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

    session_key = f'session:{session_id}:chat:{chat_id}'
    if not await rdb.exists(session_key):
        raise HTTPException(status_code=403, detail='Chat does not belong to your session')

    chat_count_key = f"session:{session_id}:count"
    chat_count = await rdb.get(chat_count_key)
    if chat_count and int(chat_count) >= 100:
        raise HTTPException(status_code=429, detail="تعداد پیام‌های روزانه بیش از حد مجاز است (حداکثر ۱۰۰ پیام)")
    else:
        await rdb.incr(chat_count_key)
        await rdb.expire(chat_count_key, 86400)

    if len(chat_in.message) > 1000:
        raise HTTPException(status_code=400, detail="پیام خیلی طولانی است (حداکثر ۱۰۰۰ کاراکتر)")

    await add_chat_messages(rdb, chat_id, [{
        'role': 'user',
        'content': chat_in.message,
        'created': int(time())
    }])

    assistant = RAGAssistant(chat_id=chat_id, rdb=rdb)
    sse_stream = assistant.run(message=chat_in.message)

    latest_response = {"content": ""}

    async def event_generator():
        async for event in sse_stream:
            if isinstance(event.data, dict) and "content" in event.data:
                latest_response["content"] += event.data["content"]
            yield event

        await add_chat_messages(rdb, chat_id, [{
            'role': 'assistant',
            'content': latest_response["content"],
            'created': int(time())
        }])

    return EventSourceResponse(event_generator(), background=rdb.aclose)
