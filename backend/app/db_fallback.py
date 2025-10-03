"""
Fallback database functions for when Redis Search is not available
"""
import json
from typing import List, Dict, Any, Optional
from redis.asyncio import Redis
from app.config import settings

def get_redis():
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

async def setup_db(rdb):
    """Setup database - fallback version"""
    print("Setting up database in fallback mode (no Redis Search)")
    return True

async def create_chat(rdb, chat_id: str, created: int):
    """Create a new chat"""
    await rdb.hset(f'chat:{chat_id}', mapping={'created': created})

async def chat_exists(rdb, chat_id: str) -> bool:
    """Check if chat exists"""
    return await rdb.exists(f'chat:{chat_id}')

async def add_chat_messages(rdb, chat_id: str, messages: List[Dict]):
    """Add messages to chat history"""
    for message in messages:
        message_json = json.dumps(message, ensure_ascii=False)
        await rdb.lpush(f'chat:{chat_id}:messages', message_json)

async def get_chat_messages(rdb, chat_id: str, last_n: int = 50) -> List[Dict]:
    """Get chat messages"""
    messages = await rdb.lrange(f'chat:{chat_id}:messages', 0, last_n - 1)
    return [json.loads(msg) for msg in reversed(messages)]

async def add_chunks_to_vector_db(rdb, chunks: List[Dict]):
    """Add chunks to vector database - fallback version"""
    print(f"Adding {len(chunks)} chunks to fallback storage")
    for i, chunk in enumerate(chunks):
        chunk_key = f"chunk:{chunk.get('chunk_id', i)}"
        await rdb.set(chunk_key, json.dumps(chunk, ensure_ascii=False))

async def search_hybrid_db(
    rdb,
    query_vector,
    query_text: str,
    top_k: int = 10,
    category: Optional[str] = None,
    budget_range: Optional[str] = None,
    alpha: float = 0.6
) -> List[Dict]:
    """Fallback search function"""
    print(f"Fallback search for: {query_text}")
    
    # Simple keyword search in stored chunks
    results = []
    
    # Get all chunk keys
    chunk_keys = await rdb.keys("chunk:*")
    
    for key in chunk_keys[:top_k * 2]:  # Get more than needed for filtering
        chunk_data = await rdb.get(key)
        if chunk_data:
            try:
                chunk = json.loads(chunk_data)
                metadata = chunk.get('metadata', {})
                
                # Simple text matching
                text = chunk.get('text', '').lower()
                name = metadata.get('name', '').lower()
                features = metadata.get('features_flat', '').lower()
                
                query_lower = query_text.lower()
                
                # Calculate simple relevance score
                score = 0.0
                if query_lower in name:
                    score += 0.8
                if query_lower in text:
                    score += 0.6
                if query_lower in features:
                    score += 0.4
                
                # Category filtering
                if category and category.lower() not in metadata.get('category', '').lower():
                    continue
                
                # Budget filtering
                if budget_range:
                    chunk_budget = metadata.get('budget_range', '')
                    if budget_range not in chunk_budget:
                        continue
                
                if score > 0:
                    results.append({
                        'metadata': metadata,
                        'text': chunk.get('text', ''),
                        'score': score,
                        'chunk_id': chunk.get('chunk_id', '')
                    })
                    
            except json.JSONDecodeError:
                continue
    
    # Sort by score and return top results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

async def search_vector_db(rdb, query_vector, top_k: int = 10, category: Optional[str] = None, budget_range: Optional[str] = None) -> List[Dict]:
    """Fallback vector search"""
    return await search_hybrid_db(rdb, query_vector, "", top_k, category, budget_range)

async def search_keyword_db(rdb, query_text: str, top_k: int = 10, category: Optional[str] = None, budget_range: Optional[str] = None) -> List[Dict]:
    """Fallback keyword search"""
    return await search_hybrid_db(rdb, None, query_text, top_k, category, budget_range)

async def get_all_vectors(rdb) -> List[Dict]:
    """Get all vectors - fallback version"""
    results = []
    chunk_keys = await rdb.keys("chunk:*")
    
    for key in chunk_keys:
        chunk_data = await rdb.get(key)
        if chunk_data:
            try:
                chunk = json.loads(chunk_data)
                results.append(chunk)
            except json.JSONDecodeError:
                continue
    
    return results

async def get_all_chats(rdb) -> List[Dict]:
    """Get all chats - fallback version"""
    chat_keys = await rdb.keys("chat:*")
    chats = []
    
    for key in chat_keys:
        if b':messages' not in key:  # Skip message keys
            chat_data = await rdb.hgetall(key)
            if chat_data:
                chat_id = key.decode().replace('chat:', '')
                chats.append({
                    'id': chat_id,
                    'created': int(chat_data.get(b'created', 0))
                })
    
    return chats

