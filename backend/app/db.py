import json
import numpy as np
from time import time
from redis.asyncio import Redis
from redis.commands.search.field import TextField, VectorField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.json.path import Path
from app.config import settings
from app.cache_manager import cache_manager

VECTOR_IDX_NAME = 'idx:vector'
VECTOR_IDX_PREFIX = 'vector:'
CHAT_IDX_NAME = 'idx:chat'
CHAT_IDX_PREFIX = 'chat:'

def get_redis():
    """دریافت اتصال Redis"""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=False
    )

# ------------------------ VECTORS ------------------------

async def create_vector_index(rdb):
    """ایجاد اندیس برداری"""
    schema = (
        TextField('$.chunk_id', no_stem=True, as_name='chunk_id'),
        TextField('$.text', as_name='text'),
        TextField('$.doc_name', as_name='doc_name'),
        VectorField(
            '$.vector',
            'FLAT',
            {
                'TYPE': 'FLOAT32',
                'DIM': settings.EMBEDDING_DIMENSIONS,
                'DISTANCE_METRIC': 'COSINE'
            },
            as_name='vector'
        )
    )
    try:
        await rdb.ft(VECTOR_IDX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(prefix=[VECTOR_IDX_PREFIX], index_type=IndexType.JSON)
        )
        print(f"Vector index '{VECTOR_IDX_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating vector index '{VECTOR_IDX_NAME}': {e}")

async def add_chunks_to_vector_db_batch(rdb, chunks, batch_size=100):
    """افزودن چانک‌ها به دیتابیس برداری به صورت دسته‌ای"""
    async with rdb.pipeline(transaction=True) as pipe:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            for chunk in batch:
                pipe.json().set(VECTOR_IDX_PREFIX + chunk['chunk_id'], Path.root_path(), chunk)
            await pipe.execute()
    
    # پاک کردن کش مرتبط پس از به‌روزرسانی داده‌ها
    await cache_manager.flush_all()

async def search_vector_db(rdb, query_vector, top_k=settings.VECTOR_SEARCH_TOP_K):
    """جستجو در دیتابیس برداری"""
    query = (
        Query(f'(*)=>[KNN {top_k} @vector $query_vector AS score]')
        .sort_by('score')
        .return_fields('score', 'chunk_id', 'text', 'doc_name')
        .dialect(2)
    )
    res = await rdb.ft(VECTOR_IDX_NAME).search(query, {
        'query_vector': np.array(query_vector, dtype=np.float32).tobytes()
    })
    return [{
        'score': 1 - float(d.score),
        'chunk_id': d.chunk_id,
        'text': d.text,
        'doc_name': d.doc_name
    } for d in res.docs]

async def get_all_vectors(rdb):
    """دریافت تمام بردارها"""
    count = await rdb.ft(VECTOR_IDX_NAME).search(Query('*').paging(0, 0))
    res = await rdb.ft(VECTOR_IDX_NAME).search(Query('*').paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]

# ------------------------ CHATS ------------------------

async def create_chat_index(rdb):
    """ایجاد اندیس چت‌ها"""
    try:
        schema = (
            NumericField('$.created', as_name='created', sortable=True),
        )
        await rdb.ft(CHAT_IDX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(prefix=[CHAT_IDX_PREFIX], index_type=IndexType.JSON)
        )
        print(f"Chat index '{CHAT_IDX_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating chat index '{CHAT_IDX_NAME}': {e}")

async def create_chat(rdb, chat_id, created, ttl_seconds=172800):
    """ایجاد چت جدید"""
    chat = {'id': chat_id, 'created': created, 'messages': []}
    key = CHAT_IDX_PREFIX + chat_id
    await rdb.json().set(key, Path.root_path(), chat)
    await rdb.expire(key, ttl_seconds)
    return chat

async def add_chat_messages(rdb, chat_id, messages):
    """افزودن پیام‌ها به چت"""
    timestamped = []
    for msg in messages:
        if 'created' not in msg:
            msg['created'] = int(time())
        timestamped.append(msg)
    await rdb.json().arrappend(CHAT_IDX_PREFIX + chat_id, '$.messages', *timestamped)

async def chat_exists(rdb, chat_id):
    """بررسی وجود چت"""
    return await rdb.exists(CHAT_IDX_PREFIX + chat_id)

async def get_chat_messages(rdb, chat_id, last_n=None):
    """دریافت پیام‌های چت"""
    if last_n is None:
        messages = await rdb.json().get(CHAT_IDX_PREFIX + chat_id, '$.messages[*]')
    else:
        messages = await rdb.json().get(CHAT_IDX_PREFIX + chat_id, f'$.messages[-{last_n}:]')
    return [{'role': m['role'], 'content': m['content']} for m in messages] if messages else []

async def get_chat(rdb, chat_id):
    """دریافت اطلاعات چت"""
    return await rdb.json().get(chat_id)

async def get_all_chats(rdb):
    """دریافت تمام چت‌ها"""
    q = Query('*').sort_by('created', asc=False)
    count = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, 0))
    res = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]

# ------------------------ GENERAL ------------------------

async def setup_db(rdb):
    """راه‌اندازی دیتابیس"""
    try:
        await rdb.ft(VECTOR_IDX_NAME).dropindex(delete_documents=True)
        print(f"Deleted vector index '{VECTOR_IDX_NAME}' and all associated documents")
    except Exception:
        pass
    finally:
        await create_vector_index(rdb)

    # اطمینان از ایجاد اندیس چت‌ها
    try:
        await rdb.ft(CHAT_IDX_NAME).dropindex(delete_documents=True)
        print(f"Deleted chat index '{CHAT_IDX_NAME}' and all associated documents")
    except Exception:
        pass
    finally:
        await create_chat_index(rdb)

async def clear_db(rdb):
    """پاک کردن دیتابیس"""
    for index_name in [VECTOR_IDX_NAME, CHAT_IDX_NAME]:
        try:
            await rdb.ft(index_name).dropindex(delete_documents=True)
            print(f"Deleted index '{index_name}' and all associated documents")
        except Exception as e:
            print(f"Index '{index_name}': {e}")
    
    # پاک کردن کش
    await cache_manager.flush_all()