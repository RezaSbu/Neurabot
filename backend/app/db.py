import json
import numpy as np
from time import time
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import settings

VECTOR_COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME
CHAT_COLLECTION_NAME = settings.QDRANT_CHAT_COLLECTION_NAME

# اتصال به Qdrant
def get_qdrant():
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

# ------------------------ VECTORS ------------------------

async def create_vector_index(qdrant):
    try:
        qdrant.create_collection(
            collection_name=VECTOR_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE
            )
        )
        print(f"Vector collection '{VECTOR_COLLECTION_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating vector collection '{VECTOR_COLLECTION_NAME}': {e}")

async def add_chunks_to_vector_db(qdrant, chunks):
    points = []
    for chunk in chunks:
        points.append(PointStruct(
            id=chunk['chunk_id'],
            vector=chunk['vector'] if chunk['vector'] else [0.0] * settings.EMBEDDING_DIMENSIONS,
            payload={
                'chunk_id': chunk['chunk_id'],
                'text': chunk['text'],
                'doc_name': chunk['doc_name'],
                'metadata': chunk['metadata']
            }
        ))
    try:
        qdrant.upsert(
            collection_name=VECTOR_COLLECTION_NAME,
            points=points
        )
        print(f"Added {len(points)} chunks to vector collection")
    except Exception as e:
        print(f"Error adding chunks to vector collection: {e}")

async def search_vector_db(qdrant, query_vector, top_k=settings.VECTOR_SEARCH_TOP_K):
    try:
        results = qdrant.search(
            collection_name=VECTOR_COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )
        return [{
            'score': 1 - result.score,
            'chunk_id': result.payload['chunk_id'],
            'text': result.payload['text'],
            'doc_name': result.payload['doc_name'],
            'metadata': result.payload['metadata']
        } for result in results]
    except Exception as e:
        print(f"Error searching vector collection: {e}")
        return []

async def get_all_vectors(qdrant):
    try:
        results = qdrant.scroll(
            collection_name=VECTOR_COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=True
        )[0]
        return [{
            'chunk_id': point.payload['chunk_id'],
            'text': point.payload['text'],
            'doc_name': point.payload['doc_name'],
            'vector': point.vector,
            'metadata': point.payload['metadata']
        } for point in results]
    except Exception as e:
        print(f"Error retrieving all vectors: {e}")
        return []

# ------------------------ CHATS ------------------------

async def create_chat_index(qdrant):
    try:
        qdrant.create_collection(
            collection_name=CHAT_COLLECTION_NAME,
            vectors_config=None  # بدون وکتور برای چت‌ها
        )
        print(f"Chat collection '{CHAT_COLLECTION_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating chat collection '{CHAT_COLLECTION_NAME}': {e}")

async def create_chat(qdrant, chat_id, created, ttl_seconds=604800):
    chat = {'id': chat_id, 'created': created, 'messages': []}
    try:
        qdrant.upsert(
            collection_name=CHAT_COLLECTION_NAME,
            points=[{
                'id': chat_id,
                'payload': chat
            }]
        )
        print(f"Chat '{chat_id}' created successfully")
        return chat
    except Exception as e:
        print(f"Error creating chat: {e}")
        return None

async def add_chat_messages(qdrant, chat_id, messages):
    timestamped = []
    for msg in messages:
        if 'created' not in msg:
            msg['created'] = int(time())
        timestamped.append(msg)
    try:
        current = qdrant.scroll(
            collection_name=CHAT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="id", match=MatchValue(value=chat_id))]
            ),
            limit=1,
            with_payload=True
        )[0]
        if current:
            current_chat = current[0].payload
            current_chat['messages'].extend(timestamped)
            qdrant.upsert(
                collection_name=CHAT_COLLECTION_NAME,
                points=[{
                    'id': chat_id,
                    'payload': current_chat
                }]
            )
            print(f"Messages added to chat '{chat_id}'")
    except Exception as e:
        print(f"Error adding chat messages: {e}")

async def chat_exists(qdrant, chat_id):
    try:
        result = qdrant.scroll(
            collection_name=CHAT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="id", match=MatchValue(value=chat_id))]
            ),
            limit=1
        )[0]
        return bool(result)
    except Exception as e:
        print(f"Error checking chat existence: {e}")
        return False

async def get_chat_messages(qdrant, chat_id, last_n=None):
    try:
        result = qdrant.scroll(
            collection_name=CHAT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="id", match=MatchValue(value=chat_id))]
            ),
            limit=1,
            with_payload=True
        )[0]
        if not result:
            return []
        messages = result[0].payload.get('messages', [])
        if last_n is not None:
            messages = messages[-last_n:]
        return [{'role': m['role'], 'content': m['content']} for m in messages]
    except Exception as e:
        print(f"Error retrieving chat messages: {e}")
        return []

async def get_all_chats(qdrant):
    try:
        results = qdrant.scroll(
            collection_name=CHAT_COLLECTION_NAME,
            limit=1000,
            with_payload=True
        )[0]
        return [point.payload for point in results]
    except Exception as e:
        print(f"Error retrieving all chats: {e}")
        return []

# ------------------------ GENERAL ------------------------

async def setup_db(qdrant):
    try:
        qdrant.delete_collection(collection_name=VECTOR_COLLECTION_NAME)
        print(f"Deleted vector collection '{VECTOR_COLLECTION_NAME}'")
    except Exception:
        pass
    finally:
        await create_vector_index(qdrant)

    try:
        qdrant.delete_collection(collection_name=CHAT_COLLECTION_NAME)
        print(f"Deleted chat collection '{CHAT_COLLECTION_NAME}'")
    except Exception:
        pass
    finally:
        await create_chat_index(qdrant)

async def clear_db(qdrant):
    for collection_name in [VECTOR_COLLECTION_NAME, CHAT_COLLECTION_NAME]:
        try:
            qdrant.delete_collection(collection_name=collection_name)
            print(f"Deleted collection '{collection_name}'")
        except Exception as e:
            print(f"Collection '{collection_name}': {e}")