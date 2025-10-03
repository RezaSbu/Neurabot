import json
import asyncio
import numpy as np
from time import time
from redis.asyncio import Redis
try:
    from redis.commands.search.field import TextField, VectorField, NumericField, TagField
    from redis.commands.search.index_definition import IndexDefinition, IndexType
    from redis.commands.search.query import Query
    from redis.commands.json.path import Path
    REDIS_SEARCH_AVAILABLE = True
except ImportError:
    # Fallback for older Redis versions
    REDIS_SEARCH_AVAILABLE = False
    print("Redis Search not available - using fallback functions")
    
    # Import fallback functions
    from app.db_fallback import (
        get_redis as fallback_get_redis,
        setup_db as fallback_setup_db,
        create_chat as fallback_create_chat,
        chat_exists as fallback_chat_exists,
        add_chat_messages as fallback_add_chat_messages,
        get_chat_messages as fallback_get_chat_messages,
        add_chunks_to_vector_db as fallback_add_chunks_to_vector_db,
        search_hybrid_db as fallback_search_hybrid_db,
        search_vector_db as fallback_search_vector_db,
        search_keyword_db as fallback_search_keyword_db,
        get_all_vectors as fallback_get_all_vectors,
        get_all_chats as fallback_get_all_chats
    )
    
    # Replace functions with fallbacks
    get_redis = fallback_get_redis
    setup_db = fallback_setup_db
    create_chat = fallback_create_chat
    chat_exists = fallback_chat_exists
    add_chat_messages = fallback_add_chat_messages
    get_chat_messages = fallback_get_chat_messages
    add_chunks_to_vector_db = fallback_add_chunks_to_vector_db
    search_hybrid_db = fallback_search_hybrid_db
    search_vector_db = fallback_search_vector_db
    search_keyword_db = fallback_search_keyword_db
    get_all_vectors = fallback_get_all_vectors
    get_all_chats = fallback_get_all_chats
from app.config import settings

VECTOR_IDX_NAME = 'idx:vector'
VECTOR_IDX_PREFIX = 'vector:'
CHAT_IDX_NAME = 'idx:chat'
CHAT_IDX_PREFIX = 'chat:'

def get_redis():
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

async def create_vector_index(rdb):
    schema = (
        TextField('$.chunk_id', no_stem=True, as_name='chunk_id'),
        TextField('$.text', as_name='text', weight=1.0),
        TextField('$.doc_name', as_name='doc_name', weight=0.5),
        TextField('$.metadata.name', as_name='name', weight=3.0),
        TextField('$.metadata.features_flat', as_name='features', weight=2.0),
        TagField('$.metadata.brand', as_name='brand'),
        TagField('$.metadata.sizes_flat[*]', as_name='sizes'),
        TagField('$.metadata.category', as_name='category'),
        TagField('$.metadata.budget_range', as_name='budget_range'),
        VectorField(
            '$.vector',
            'HNSW',
            {
                'TYPE': 'FLOAT32',
                'DIM': settings.EMBEDDING_DIMENSIONS,
                'DISTANCE_METRIC': 'COSINE',
                'M': 40,
                'EF_CONSTRUCTION': 200
            },
            as_name='vector'
        )
    )
    try:
        await rdb.ft(VECTOR_IDX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(prefix=[VECTOR_IDX_PREFIX], index_type=IndexType.JSON)
        )
        print(f"Vector index '{VECTOR_IDX_NAME}' created successfully with HNSW")
    except Exception as e:
        print(f"Error creating vector index '{VECTOR_IDX_NAME}': {e}")

async def add_chunks_to_vector_db(rdb, chunks):
    async with rdb.pipeline(transaction=True) as pipe:
        for chunk in chunks:
            pipe.json().set(VECTOR_IDX_PREFIX + chunk['chunk_id'], Path.root_path(), chunk)
        await pipe.execute()

async def search_vector_db(rdb, query_vector, top_k=settings.VECTOR_SEARCH_TOP_K, category=None, budget_range=None):
    query_str = f'(*)=>[KNN {top_k} @vector $query_vector AS score]'
    if category:
        query_str = f'(@category:{{{category}}})=>[KNN {top_k} @vector $query_vector AS score]'
    if budget_range:
        query_str = f'(@budget_range:{{{budget_range}}})=>[KNN {top_k} @vector $query_vector AS score]'
    if category and budget_range:
        query_str = f'(@category:{{{category}}} @budget_range:{{{budget_range}}})=>[KNN {top_k} @vector $query_vector AS score]'
    
    query = (
        Query(query_str)
        .sort_by('score')
        # Return only the score; we'll read full JSON from doc.json
        .return_fields('score')
        .dialect(2)
    )
    res = await rdb.ft(VECTOR_IDX_NAME).search(query, {
        'query_vector': np.array(query_vector, dtype=np.float32).tobytes()
    })
    results = []
    for d in res.docs:
        try:
            full_doc = json.loads(d.json)
        except Exception:
            full_doc = {}
        full_doc['score'] = 1 - float(d.score)
        results.append(full_doc)
    return results

async def search_keyword_db(rdb, query_text, top_k=settings.VECTOR_SEARCH_TOP_K, category=None, budget_range=None):
    # Helpers
    def escape_tag_value(val: str) -> str:
        if val is None:
            return ''
        # Escape spaces and braces for TAG values
        return val.replace(' ', '\\ ').replace('{', '\\{').replace('}', '\\}')

    # Weighted field query: prioritize name > features > text
    if query_text and query_text.strip():
        escaped = query_text.replace('"', '\\"')
        base_query = f'((@name:"{escaped}") | (@features:"{escaped}") | (@text:"{escaped}"))'
    else:
        base_query = "*"

    cat_filter = f'@category:{{{escape_tag_value(category)}}}' if category else ''
    bud_filter = f'@budget_range:{{{escape_tag_value(budget_range)}}}' if budget_range else ''
    filters = ' '.join([f for f in [cat_filter, bud_filter] if f])
    query_str = f'{filters} {base_query}'.strip()

    query = (
        Query(query_str)
        .return_fields('score')
        .paging(0, top_k)
        .dialect(2)
    )
    res = await rdb.ft(VECTOR_IDX_NAME).search(query)
    results = []
    for d in res.docs:
        try:
            full_doc = json.loads(d.json)
        except Exception:
            full_doc = {}
        # RediSearch BM25 returns a numeric score; higher is better. Keep as-is for normalization later
        try:
            kw_score = float(d.score)
        except Exception:
            kw_score = 0.0
        full_doc['kw_score'] = kw_score
        results.append(full_doc)
    return results

async def search_hybrid_db(
    rdb,
    query_vector,
    query_text,
    top_k=settings.VECTOR_SEARCH_TOP_K,
    category=None,
    budget_range=None,
    alpha: float = 0.6,
):
    # Run vector and keyword searches independently
    vec_results, kw_results = await asyncio.gather(
        search_vector_db(rdb, query_vector, top_k=top_k, category=category, budget_range=budget_range),
        search_keyword_db(rdb, query_text, top_k=top_k, category=category, budget_range=budget_range),
    )

    # Normalize vector scores (already 0..1 roughly). Ensure in [0,1]
    for r in vec_results:
        r['vec_score'] = max(0.0, min(1.0, float(r.get('score', 0.0))))

    # Normalize keyword scores using min-max over present scores
    kw_scores = [float(r.get('kw_score', 0.0)) for r in kw_results if r.get('kw_score') is not None]
    if kw_scores:
        kw_min, kw_max = min(kw_scores), max(kw_scores)
        denom = (kw_max - kw_min) or 1.0
        for r in kw_results:
            r['kw_score_norm'] = (float(r.get('kw_score', 0.0)) - kw_min) / denom
    else:
        for r in kw_results:
            r['kw_score_norm'] = 0.0

    # Merge by chunk_id
    by_id = {}
    def cid(doc):
        return doc.get('chunk_id') or doc.get('metadata', {}).get('chunk_id')

    for r in vec_results:
        key = cid(r) or r.get('chunk_id')
        if not key:
            key = r.get('metadata', {}).get('product_id') or id(r)
        by_id[key] = r
        by_id[key]['kw_score_norm'] = by_id[key].get('kw_score_norm', 0.0)

    for r in kw_results:
        key = cid(r) or r.get('chunk_id')
        if not key:
            key = r.get('metadata', {}).get('product_id') or id(r)
        if key in by_id:
            by_id[key]['kw_score_norm'] = r.get('kw_score_norm', 0.0)
        else:
            # ensure vec score exists
            r['vec_score'] = max(0.0, min(1.0, float(r.get('score', 0.0))))
            by_id[key] = r

    # Compute combined score
    combined = []
    for doc in by_id.values():
        vec_s = float(doc.get('vec_score', doc.get('score', 0.0)))
        kw_s = float(doc.get('kw_score_norm', 0.0))
        doc['hybrid_score'] = alpha * vec_s + (1 - alpha) * kw_s
        combined.append(doc)

    # Sort by combined score desc and return top_k
    combined.sort(key=lambda d: d.get('hybrid_score', 0.0), reverse=True)
    return combined[:top_k]

async def get_all_vectors(rdb):
    count = await rdb.ft(VECTOR_IDX_NAME).search(Query('*').paging(0, 0))
    res = await rdb.ft(VECTOR_IDX_NAME).search(Query('*').paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]

async def create_chat_index(rdb):
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
    chat = {'id': chat_id, 'created': created, 'messages': []}
    key = CHAT_IDX_PREFIX + chat_id
    await rdb.json().set(key, Path.root_path(), chat)
    await rdb.expire(key, ttl_seconds)
    return chat

async def add_chat_messages(rdb, chat_id, messages):
    timestamped = []
    for msg in messages:
        if 'created' not in msg:
            msg['created'] = int(time())
        timestamped.append(msg)
    await rdb.json().arrappend(CHAT_IDX_PREFIX + chat_id, '$.messages', *timestamped)

async def chat_exists(rdb, chat_id):
    return await rdb.exists(CHAT_IDX_PREFIX + chat_id)

async def get_chat_messages(rdb, chat_id, last_n=None):
    if last_n is None:
        messages = await rdb.json().get(CHAT_IDX_PREFIX + chat_id, '$.messages[*]')
    else:
        messages = await rdb.json().get(CHAT_IDX_PREFIX + chat_id, f'$.messages[-{last_n}:]')
    return [{'role': m['role'], 'content': m['content']} for m in messages] if messages else []

async def get_chat(rdb, chat_id):
    return await rdb.json().get(chat_id)

async def get_all_chats(rdb):
    q = Query('*').sort_by('created', asc=False)
    count = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, 0))
    res = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]

async def setup_db(rdb):
    try:
        await rdb.ft(VECTOR_IDX_NAME).dropindex(delete_documents=True)
        print(f"Deleted vector index '{VECTOR_IDX_NAME}' and all associated documents")
    except Exception:
        pass
    finally:
        await create_vector_index(rdb)

    try:
        await rdb.ft(CHAT_IDX_NAME).info()
    except Exception:
        await create_chat_index(rdb)

async def clear_db(rdb):
    for index_name in [VECTOR_IDX_NAME, CHAT_IDX_NAME]:
        try:
            await rdb.ft(index_name).dropindex(delete_documents=True)
            print(f"Deleted index '{index_name}' and all associated documents")
        except Exception as e:
            print(f"Index '{index_name}': {e}")