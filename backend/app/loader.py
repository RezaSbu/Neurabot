"""
اسکریپت بارگذاری اسناد:
۱. اسناد JSON را می‌خواند
2. متن را به چانک تبدیل می‌کند
3. برای هر چانک embedding می‌سازد
4. همه را در Qdrant upsert می‌کند
"""

import os, json, asyncio
from uuid import uuid4
from tqdm import tqdm
from typing import List, Dict

from app.config import settings
from app.db import recreate_product_collection, upsert_chunks
from app.openai import get_embedding, token_size
from app.utils.splitter import TextSplitter

# ---------- کمک‌کننده ----------
def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def batch(lst, n=512):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

# ---------- پردازش ----------
async def build_chunks(docs_dir: str) -> List[Dict]:
    splitter = TextSplitter(chunk_size=512, chunk_overlap=150)
    chunks: List[Dict] = []

    files = [f for f in os.listdir(docs_dir) if f.endswith(".json")]
    for fn in files:
        data = load_json(os.path.join(docs_dir, fn))
        for item in data:
            meta = item | {"doc_name": item.get("title", "")}
            text_src = (
                item.get("description") or item.get("title") or "بدون توضیح"
            )
            for part in splitter.split(text_src):
                emb = await get_embedding(part)
                chunks.append(
                    {
                        "chunk_id": str(uuid4()),
                        "vector": emb,
                        "metadata": meta | {"text": part},
                    }
                )
    return chunks

async def process_docs() -> None:
    # 1) ساخت مجموعهٔ برداری تازه
    recreate_product_collection()

    # 2) چانک و امبدینگ
    chunks = await build_chunks(settings.DOCS_DIR)
    print(f"Total chunks: {len(chunks)}")

    # 3) آپسرت دسته‌ای
    for b in tqdm(list(batch(chunks, 500)), desc="Upserting to Qdrant"):
        upsert_chunks(b)

# ---------- entry ----------
def main():
    asyncio.run(process_docs())

if __name__ == "__main__":
    main()
