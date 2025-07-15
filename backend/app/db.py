import json
import numpy as np
from time import time
from redis.asyncio import Redis
from redis.commands.search.field import TextField, VectorField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.json.path import Path
from app.config import settings

VECTOR_IDX_NAME = 'idx:vector'
VECTOR_IDX_PREFIX = 'vector:'
CHAT_IDX_NAME = 'idx:chat'
CHAT_IDX_PREFIX = 'chat:'


def get_redis() -> Redis:
    """Establish a Redis connection using settings."""
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


# ------------------------ VECTOR INDEX ------------------------

async def create_vector_index(rdb: Redis):
    """
    Create a RediSearch vector index for document chunks.
    """
    schema = (
        TextField('$.chunk_id', no_stem=True, as_name='chunk_id'),
        TextField('$.text', as_name='text'),
        TextField('$.doc_name', as_name='doc_name'),
        VectorField(
            '$.vector', 'FLAT', {
                'TYPE': 'FLOAT32',
                'DIM': settings.EMBEDDING_DIMENSIONS,
                'DISTANCE_METRIC': 'COSINE'
            }, as_name='vector'
        ),
    )
    try:
        await rdb.ft(VECTOR_IDX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(
                prefix=[VECTOR_IDX_PREFIX],
                index_type=IndexType.JSON
            )
        )
        print(f"Vector index '{VECTOR_IDX_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating vector index '{VECTOR_IDX_NAME}': {e}")


async def add_chunks_to_vector_db(rdb: Redis, chunks: list[dict]):
    """
    Add a list of chunk dicts to the vector index using Redis JSON.
    """
    async with rdb.pipeline(transaction=True) as pipe:
        for chunk in chunks:
            pipe.json().set(
                VECTOR_IDX_PREFIX + chunk['chunk_id'],
                Path.root_path(),
                chunk
            )
        await pipe.execute()


async def search_vector_db(rdb: Redis, query_vector: list[float], filters: dict = None, top_k: int = None):
    """
    Hybrid search: apply metadata filters then perform KNN vector search.
    filters keys: 'query_category', 'brand', etc.
    """
    if top_k is None:
        top_k = settings.VECTOR_SEARCH_TOP_K

    # Build metadata filter clauses
    where_clauses = []
    if filters:
        if filters.get('query_category'):
            where_clauses.append(f"@category:{{{filters['query_category']}}}")
        if filters.get('brand'):
            where_clauses.append(f"@brand:{{{filters['brand']}}}")
    prefix = ' '.join(where_clauses) if where_clauses else '*'

    # Compose RediSearch query
    query = (
        Query(f'({prefix})=>[KNN {top_k} @vector $q AS score]')
        .sort_by('score')
        .return_fields('score', 'chunk_id', 'text', 'doc_name')
        .dialect(2)
    )
    res = await rdb.ft(VECTOR_IDX_NAME).search(
        query,
        {'q': np.array(query_vector, dtype=np.float32).tobytes()}
    )
    return [
        {
            'score': 1 - float(doc.score),
            'chunk_id': doc.chunk_id,
            'text': doc.text,
            'doc_name': doc.doc_name
        }
        for doc in res.docs
    ]


async def get_all_vectors(rdb: Redis) -> list[dict]:
    """Retrieve all vector documents from the index."""
    count = await rdb.ft(VECTOR_IDX_NAME).search(Query('*').paging(0, 0))
    res = await rdb.ft(VECTOR_IDX_NAME).search(Query('*').paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]


# ------------------------ CHAT INDEX ------------------------

async def create_chat_index(rdb: Redis):
    """
    Create a RediSearch index for chat metadata.
    """
    try:
        schema = (NumericField('$.created', as_name='created', sortable=True),)
        await rdb.ft(CHAT_IDX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(
                prefix=[CHAT_IDX_PREFIX], index_type=IndexType.JSON
            )
        )
        print(f"Chat index '{CHAT_IDX_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating chat index '{CHAT_IDX_NAME}': {e}")


async def create_chat(rdb: Redis, chat_id: str, created: int, ttl_seconds: int = 604800):
    """
    Initialize a new chat record with TTL (defaults to 7 days).
    """
    chat = {'id': chat_id, 'created': created, 'messages': []}
    key = CHAT_IDX_PREFIX + chat_id
    await rdb.json().set(key, Path.root_path(), chat)
    await rdb.expire(key, ttl_seconds)
    return chat


async def add_chat_messages(rdb: Redis, chat_id: str, messages: list[dict]):
    """
    Append user/assistant messages into chat JSON array.
    """
    timestamped = []
    for msg in messages:
        if 'created' not in msg:
            msg['created'] = int(time())
        timestamped.append(msg)
    await rdb.json().arrappend(
        CHAT_IDX_PREFIX + chat_id,
        '$.messages',
        *timestamped
    )


async def chat_exists(rdb: Redis, chat_id: str) -> bool:
    """Check if a chat record key exists."""
    return (await rdb.exists(CHAT_IDX_PREFIX + chat_id)) > 0


async def get_chat_messages(rdb: Redis, chat_id: str, last_n: int = None) -> list[dict]:
    """
    Fetch last_n messages or all messages if last_n None.
    """
    if last_n is None:
        messages = await rdb.json().get(CHAT_IDX_PREFIX + chat_id, '$.messages[*]')
    else:
        messages = await rdb.json().get(
            CHAT_IDX_PREFIX + chat_id,
            f'$.messages[-{last_n}:]'
        )
    return (
        [{'role': m['role'], 'content': m['content']} for m in messages]
        if messages else []
    )


async def get_chat(rdb: Redis, chat_id: str) -> dict:
    """Get full chat JSON."""
    return await rdb.json().get(CHAT_IDX_PREFIX + chat_id)


async def get_all_chats(rdb: Redis) -> list[dict]:
    """Retrieve all chats sorted by creation time desc."""
    q = Query('*').sort_by('created', asc=False)
    count = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, 0))
    res = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]


# ------------------------ DB SETUP / TEARDOWN ------------------------

async def setup_db(rdb: Redis):
    """Recreate indices for a clean start."""
    try:
        await rdb.ft(VECTOR_IDX_NAME).dropindex(delete_documents=True)
    except Exception:
        pass
    await create_vector_index(rdb)

    try:
        await rdb.ft(CHAT_IDX_NAME).info()
    except Exception:
        await create_chat_index(rdb)


async def clear_db(rdb: Redis):
    """Drop both vector and chat indices."""
    for idx in [VECTOR_IDX_NAME, CHAT_IDX_NAME]:
        try:
            await rdb.ft(idx).dropindex(delete_documents=True)
            print(f"Deleted index '{idx}' and all documents")
        except Exception as e:
            print(f"Error dropping index '{idx}': {e}")
