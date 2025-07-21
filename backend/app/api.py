# from uuid import uuid4
# from time import time
# from fastapi import APIRouter, Depends, HTTPException, Header
# from pydantic import BaseModel
# from sse_starlette.sse import EventSourceResponse
# from app.db import get_redis, create_chat, chat_exists, add_chat_messages
# from app.assistants.assistant import RAGAssistant

# class ChatIn(BaseModel):
#     message: str

# async def get_rdb():
#     rdb = get_redis()
#     try:
#         yield rdb
#     finally:
#         await rdb.aclose()

# router = APIRouter()

# @router.post('/chats')
# async def create_new_chat(
#     rdb = Depends(get_rdb),
#     session_id: str = Header(..., alias='X-Session-ID')
# ):
#     chat_id = str(uuid4())[:8]
#     created = int(time())
#     await create_chat(rdb, chat_id, created)
#     await rdb.set(f'session:{session_id}:chat:{chat_id}', 1, ex=604800)  # نگهداری در Redis برای ۷ روز
#     return {'id': chat_id}

# @router.post('/chats/{chat_id}')
# async def chat(chat_id: str, chat_in: ChatIn, session_id: str = Header(..., alias='X-Session-ID')):
#     rdb = get_redis()

#     if not await chat_exists(rdb, chat_id):
#         raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

#     session_key = f'session:{session_id}:chat:{chat_id}'
#     if not await rdb.exists(session_key):
#         raise HTTPException(status_code=403, detail='Chat does not belong to your session')

#     await add_chat_messages(rdb, chat_id, [{
#         'role': 'user',
#         'content': chat_in.message,
#         'created': int(time())
#     }])

#     assistant = RAGAssistant(chat_id=chat_id, rdb=rdb)
#     sse_stream = assistant.run(message=chat_in.message)

#     latest_response = {"content": ""}

#     async def event_generator():
#         async for event in sse_stream:
#             if isinstance(event.data, dict) and "content" in event.data:
#                 latest_response["content"] += event.data["content"]
#             yield event

#         await add_chat_messages(rdb, chat_id, [{
#             'role': 'assistant',
#             'content': latest_response["content"],
#             'created': int(time())
#         }])

#     return EventSourceResponse(event_generator(), background=rdb.aclose)








from uuid import uuid4
from time import time
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.db import get_redis, create_chat, chat_exists, add_chat_messages
from app.assistants.assistant import RAGAssistant

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
async def create_new_chat(
    request: Request,
    rdb = Depends(get_rdb),
    session_id: str = Header(..., alias='X-Session-ID')
):
    chat_id = str(uuid4())[:8]
    created = int(time())
    client_ip = request.client.host

    await create_chat(rdb, chat_id, created)
    await rdb.set(f'session:{session_id}:chat:{chat_id}', 1, ex=604800)
    await rdb.set(f'session:{session_id}:ip', client_ip, ex=604800)

    return {'id': chat_id}

@router.post('/chats/{chat_id}')
async def chat(chat_id: str, chat_in: ChatIn, session_id: str = Header(..., alias='X-Session-ID')):
    rdb = get_redis()

    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

    session_key = f'session:{session_id}:chat:{chat_id}'
    if not await rdb.exists(session_key):
        raise HTTPException(status_code=403, detail='Chat does not belong to your session')

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
