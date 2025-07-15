# filename: db.py
import json
import numpy as np
from time import time
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
from app.config import settings

# Qdrant client
def get_qdrant_client():
    return QdrantClient(url=settings.QDRANT_URL)

# ------------------------ VECTORS ------------------------

async def create_vector_index(client: QdrantClient):
    try:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE
            )
        )
        print(f"Qdrant collection '{settings.QDRANT_COLLECTION_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating Qdrant collection: {e}")

async def add_chunks_to_vector_db(client: QdrantClient, chunks):
    points = []
    for chunk in chunks:
        point = PointStruct(
            id=chunk['chunk_id'],
            vector=chunk['vector'],
            payload={
                'chunk_id': chunk['chunk_id'],
                'text': chunk['text'],
                'doc_name': chunk['doc_name'],
                'metadata': chunk['metadata']
            }
        )
        points.append(point)
    
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=points
    )

async def search_vector_db(client: QdrantClient, query_vector, top_k=settings.VECTOR_SEARCH_TOP_K, filters=None):
    search_filters = Filter(must=[])
    if filters:
        for key, value in filters.items():
            if isinstance(value, dict) and 'min' in value and 'max' in value:
                search_filters.must.append(
                    FieldCondition(
                        key=key,
                        range=Range(gte=value['min'], lte=value['max'])
                    )
                )
            elif isinstance(value, dict) and 'contains_any' in value:
                search_filters.must.append(
                    FieldCondition(
                        key=key,
                        match={'any': value['contains_any']}
                    )
                )
            else:
                search_filters.must.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True,
        query_filter=search_filters if search_filters.must else None
    )

    return [{
        'score': hit.score,
        'chunk_id': hit.payload['chunk_id'],
        'text': hit.payload['text'],
        'doc_name': hit.payload['doc_name'],
        'metadata': hit.payload['metadata']
    } for hit in results]

async def get_all_vectors(client: QdrantClient):
    results = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        limit=10000
    )
    return [hit.payload for hit in results[0]]

# ------------------------ CHATS ------------------------

async def create_chat_index(client: QdrantClient):
    try:
        client.create_collection(
            collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
            vectors_config=None  # No vectors for chats
        )
        print(f"Qdrant chat collection '{settings.QDRANT_CHAT_COLLECTION_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating Qdrant chat collection: {e}")

async def create_chat(client: QdrantClient, chat_id: str, created: int, ttl_seconds: int = 604800):
    chat = {'id': chat_id, 'created': created, 'messages': []}
    point = PointStruct(
        id=chat_id,
        vector=None,
        payload=chat
    )
    client.upsert(
        collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
        points=[point]
    )
    # Set TTL (Qdrant supports TTL via retention policies, but we simulate with manual cleanup)
    return chat

async def add_chat_messages(client: QdrantClient, chat_id: str, messages: list):
    timestamped = []
    for msg in messages:
        if 'created' not in msg:
            msg['created'] = int(time())
        timestamped.append(msg)
    
    # Retrieve existing chat
    results = client.scroll(
        collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
        scroll_filter=Filter(must=[FieldCondition(key='id', match=MatchValue(value=chat_id))])
    )
    if not results[0]:
        return

    chat = results[0][0].payload
    chat['messages'].extend(timestamped)
    
    # Update chat
    client.upsert(
        collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
        points=[PointStruct(id=chat_id, vector=None, payload=chat)]
    )

async def chat_exists(client: QdrantClient, chat_id: str):
    results = client.scroll(
        collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
        scroll_filter=Filter(must=[FieldCondition(key='id', match=MatchValue(value=chat_id))])
    )
    return bool(results[0])

async def get_chat_messages(client: QdrantClient, chat_id: str, last_n: int = None):
    results = client.scroll(
        collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
        scroll_filter=Filter(must=[FieldCondition(key='id', match=MatchValue(value=chat_id))])
    )
    if not results[0]:
        return []
    
    messages = results[0][0].payload.get('messages', [])
    if last_n is not None:
        messages = messages[-last_n:]
    return [{'role': m['role'], 'content': m['content']} for m in messages]

async def get_all_chats(client: QdrantClient):
    results = client.scroll(
        collection_name=settings.QDRANT_CHAT_COLLECTION_NAME,
        limit=10000
    )
    return [hit.payload for hit in results[0]]

# ------------------------ GENERAL ------------------------

async def setup_db():
    client = get_qdrant_client()
    await create_vector_index(client)
    await create_chat_index(client)

async def clear_db():
    client = get_qdrant_client()
    try:
        client.delete_collection(settings.QDRANT_COLLECTION_NAME)
        print(f"Deleted Qdrant collection '{settings.QDRANT_COLLECTION_NAME}'")
    except Exception as e:
        print(f"Qdrant vector collection clear error: {e}")
    try:
        client.delete_collection(settings.QDRANT_CHAT_COLLECTION_NAME)
        print(f"Deleted Qdrant chat collection '{settings.QDRANT_CHAT_COLLECTION_NAME}'")
    except Exception as e:
        print(f"Qdrant chat collection clear error: {e}")