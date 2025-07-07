from uuid import uuid4
from time import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.db import get_redis, create_chat, chat_exists, add_chat_messages
from app.assistants.assistant import RAGAssistant

class ChatIn(BaseModel):
    message: str

# گرفتن Redis از تنظیمات
async def get_rdb():
    rdb = get_redis()
    try:
        yield rdb
    finally:
        await rdb.aclose()

router = APIRouter()

# 📌 ساخت چت جدید
@router.post('/chats')
async def create_new_chat(rdb = Depends(get_rdb)):
    chat_id = str(uuid4())[:8]
    created = int(time())
    await create_chat(rdb, chat_id, created)
    return {'id': chat_id}

# 📌 ارسال پیام به چت و دریافت پاسخ به صورت استریم + ذخیره پیام‌ها
@router.post('/chats/{chat_id}')
async def chat(chat_id: str, chat_in: ChatIn):
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



