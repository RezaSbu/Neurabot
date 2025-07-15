from uuid import uuid4
from time import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.db import get_qdrant, create_chat, chat_exists, add_chat_messages
from app.assistants.assistant import RAGAssistant

class ChatIn(BaseModel):
    message: str

# گرفتن Qdrant از تنظیمات
def get_qdrant_dep():
    qdrant = get_qdrant()
    try:
        yield qdrant
    finally:
        # QdrantClient نیازی به بستن دستی ندارد
        pass

router = APIRouter()

# 📌 ساخت چت جدید
@router.post('/chats')
async def create_new_chat(qdrant=Depends(get_qdrant_dep)):
    chat_id = str(uuid4())  # استفاده از UUID کامل
    created = int(time())
    await create_chat(qdrant, chat_id, created)
    return {'id': chat_id}

# 📌 ارسال پیام به چت و دریافت پاسخ به صورت استریم + ذخیره پیام‌ها
@router.post('/chats/{chat_id}')
async def chat(chat_id: str, chat_in: ChatIn, qdrant=Depends(get_qdrant_dep)):
    if not await chat_exists(qdrant, chat_id):
        raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

    # ✅ ذخیره پیام کاربر با timestamp
    await add_chat_messages(qdrant, chat_id, [{
        'role': 'user',
        'content': chat_in.message,
        'created': int(time())
    }])

    assistant = RAGAssistant(chat_id=chat_id, qdrant=qdrant)
    sse_stream = assistant.run(message=chat_in.message)

    latest_response = {"content": ""}

    # ✅ استریم پاسخ دستیار و ذخیره پیام نهایی پس از پایان
    async def event_generator():
        async for event in sse_stream:
            if isinstance(event.data, dict) and "content" in event.data:
                latest_response["content"] += event.data["content"]
            yield event

        # ✅ ذخیره پاسخ دستیار در Qdrant
        await add_chat_messages(qdrant, chat_id, [{
            'role': 'assistant',
            'content': latest_response["content"],
            'created': int(time())
        }])

    return EventSourceResponse(event_generator())