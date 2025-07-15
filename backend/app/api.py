from uuid import uuid4
from time import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.db import get_redis, create_chat, chat_exists, add_chat_messages
from app.assistants.assistant import RAGAssistant
import structlog

logger = structlog.get_logger()

class ChatIn(BaseModel):
    message: str

async def get_rdb():
    rdb = get_redis()
    try:
        yield rdb
    finally:
        await rdb.aclose()

router = APIRouter()

@router.post('/chats')
async def create_new_chat(rdb = Depends(get_rdb)):
    chat_id = str(uuid4())[:8]
    created = int(time())
    await create_chat(rdb, chat_id, created)
    logger.info("New chat created", chat_id=chat_id)
    return {'id': chat_id}

@router.post('/chats/{chat_id}')
async def chat(chat_id: str, chat_in: ChatIn):
    rdb = get_redis()

    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

    await add_chat_messages(rdb, chat_id, [{
        'role': 'user',
        'content': chat_in.message,
        'created': int(time())
    }])

    assistant = RAGAssistant(chat_id=chat_id, rdb=rdb)
    sse_stream = assistant.run(message=chat_in.message)

    latest_response = {"content": ""}

    async def event_generator():
        try:
            async for event in sse_stream:
                if isinstance(event.data, dict) and "content" in event.data:
                    latest_response["content"] += event.data["content"]
                yield event

            await add_chat_messages(rdb, chat_id, [{
                'role': 'assistant',
                'content': latest_response["content"],
                'created': int(time())
            }])
            logger.info("Chat message processed", chat_id=chat_id)
        except Exception as e:
            logger.error("Error in chat stream", exc_info=True)
            yield {"data": {"error": str(e)}}

    return EventSourceResponse(event_generator(), background=rdb.aclose)