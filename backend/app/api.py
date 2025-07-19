from uuid import uuid4
from time import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.db import get_redis, create_chat, chat_exists, add_chat_messages, get_chat_messages
from app.assistants.assistant import RAGAssistant
from app.auth import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

class ChatIn(BaseModel):
    message: str

# گرفتن Redis از تنظیمات
async def get_rdb():
    rdb = get_redis()
    try:
        yield rdb
    finally:
        await rdb.aclose()

# تنظیم Limiter برای روتر
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

# 📌 ساخت چت جدید
@router.post('/chats')
@limiter.limit("100/minute")
async def create_new_chat(request: Request, rdb=Depends(get_rdb), user=Depends(get_current_user)):
    chat_id = str(uuid4())[:8]
    created = int(time())
    await create_chat(rdb, chat_id, created)
    return {'id': chat_id}

# 📌 ارسال پیام به چت و دریافت پاسخ به صورت استریم + ذخیره پیام‌ها
@router.post('/chats/{chat_id}')
@limiter.limit("100/minute")
async def chat(request: Request, chat_id: str, chat_in: ChatIn, user=Depends(get_current_user)):
    rdb = get_redis()

    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

    # ✅ ذخیره پیام کاربر با timestamp
    await add_chat_messages(rdb, chat_id, [{
        'role': 'user',
        'content': chat_in.message,
        'created': int(time())
    }])

    assistant = RAGAssistant(chat_id=chat_id, rdb=rdb)
    sse_stream = assistant.run(message=chat_in.message)

    latest_response = {"content": ""}

    # ✅ استریم پاسخ دستیار و ذخیره پیام نهایی پس از پایان
    async def event_generator():
        async for event in sse_stream:
            if isinstance(event.data, dict) and "content" in event.data:
                latest_response["content"] += event.data["content"]
            yield event

        # ✅ ذخیره پاسخ دستیار در Redis
        await add_chat_messages(rdb, chat_id, [{
            'role': 'assistant',
            'content': latest_response["content"],
            'created': int(time())
        }])

    return EventSourceResponse(event_generator(), background=rdb.aclose)

# 📌 دریافت پیام‌های چت (برای sync UX)
@router.get('/chats/{chat_id}/messages')
@limiter.limit("100/minute")
async def get_messages(request: Request, chat_id: str, user=Depends(get_current_user)):
    rdb = get_redis()
    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404)
    messages = await get_chat_messages(rdb, chat_id)
    await rdb.aclose()
    return messages