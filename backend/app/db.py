"""
لایهٔ داده: همه‌چیز در Qdrant نگهداری می‌شود؛
- collection «products» برای بردار های اسناد
- collection «chats»   برای ذخیرۀ چت‌ها (بدون بردار واقعی؛ یک بُعد صفر)
"""

from __future__ import annotations
import json
from time import time
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from app.config import settings

# ---------- Qdrant ----------
qdrant = QdrantClient(url=settings.QDRANT_URL)

# ----------- vectors (products) -----------
def recreate_product_collection() -> None:
    """Drop & create مجموعهٔ برداری محصولات."""
    name = settings.QDRANT_COLLECTION_NAME
    try:
        qdrant.delete_collection(name)
    except Exception:
        pass
    qdrant.recreate_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=settings.EMBEDDING_DIMENSIONS, distance=Distance.COSINE
        ),
    )

def upsert_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Upsert لیستی از چانک‌ها به Qdrant."""
    pts = [
        PointStruct(
            id=chunk["chunk_id"],
            vector=chunk["vector"],
            payload=chunk["metadata"],
        )
        for chunk in chunks
    ]
    qdrant.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=pts)

def search_vectors(
    query_vector: List[float], top_k: int | None = None
) -> List[Dict[str, Any]]:
    """K-NN search در محصولات."""
    res = qdrant.search(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k or settings.VECTOR_SEARCH_TOP_K,
        with_payload=True,
    )
    return [
        {
            "score": 1 - hit.score,
            "chunk_id": str(hit.id),
            "text": hit.payload.get("text", ""),
            "doc_name": hit.payload.get("doc_name", ""),
        }
        for hit in res
    ]

def fetch_all_vectors() -> List[Dict[str, Any]]:
    """برگرداندن همۀ بردارها (برای ابزارهای آفلاین)."""
    points, _ = qdrant.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        with_payload=True,
        limit=100_000,
    )
    return [
        {"chunk_id": str(pt.id), "vector": pt.vector, "metadata": pt.payload}
        for pt in points
    ]

# ----------- chats (بدون Redis) -----------
CHAT_COLL = "chats"
# از بُعد 1 و مقدار صفر استفاده می‌کنیم (چت به بردار نیاز ندارد)
def ensure_chat_collection() -> None:
    if CHAT_COLL not in [c.name for c in qdrant.get_collections().collections]:
        qdrant.create_collection(
            collection_name=CHAT_COLL,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )

def chat_exists(chat_id: str) -> bool:
    ensure_chat_collection()
    res = qdrant.retrieve(collection_name=CHAT_COLL, ids=[chat_id])
    return bool(res)

def create_chat(chat_id: str) -> None:
    ensure_chat_collection()
    ts = int(time())
    pt = PointStruct(
        id=chat_id,
        vector=[0.0],
        payload={"created": ts, "messages": []},
    )
    qdrant.upsert(collection_name=CHAT_COLL, points=[pt])

def add_chat_messages(chat_id: str, msgs: List[Dict[str, Any]]) -> None:
    ensure_chat_collection()
    rec = qdrant.retrieve(collection_name=CHAT_COLL, ids=[chat_id])[0]
    stored = rec.payload
    stored_msgs = stored.get("messages", [])
    ts = int(time())
    for m in msgs:
        m.setdefault("created", ts)
        stored_msgs.append(m)
    stored["messages"] = stored_msgs
    qdrant.set_payload(
        collection_name=CHAT_COLL,
        payload=stored,
        points=[chat_id],
        overwrite=True,
    )

def get_chat_messages(chat_id: str, last_n: int | None = None) -> List[Dict[str, Any]]:
    ensure_chat_collection()
    rec = qdrant.retrieve(collection_name=CHAT_COLL, ids=[chat_id])[0]
    msgs: List[Dict[str, Any]] = rec.payload.get("messages", [])
    return msgs[-last_n:] if last_n else msgs

def get_all_chats() -> List[Dict[str, Any]]:
    ensure_chat_collection()
    pts, _ = qdrant.scroll(collection_name=CHAT_COLL, with_payload=True, limit=100_000)
    return [pt.payload for pt in pts]
