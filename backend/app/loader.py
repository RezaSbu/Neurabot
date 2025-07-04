import json
import os
import asyncio
from uuid import uuid4
from tqdm import tqdm
from app.utils.splitter import TextSplitter
from app.openai import get_embeddings, token_size
from app.db import get_redis, setup_db, add_chunks_to_vector_db
from app.config import settings

def batchify(iterable, batch_size):
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i + batch_size]

def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {path}: {e}")
        return []

def normalize_budget_range(price_numeric):
    """نرمال‌سازی budget_range برای جستجوی بهتر"""
    if not isinstance(price_numeric, (int, float)):
        return "unknown"
    if price_numeric < 500_000:
        return "under_500k"
    elif 500_000 <= price_numeric <= 3_000_000:
        return "500k_to_3m"
    elif 3_000_000 < price_numeric <= 5_000_000:
        return "3m_to_5m"
    elif 5_000_000 < price_numeric <= 10_000_000:
        return "5m_to_10m"
    elif 10_000_000 < price_numeric <= 20_000_000:
        return "10m_to_20m"
    else:
        return "over_20m"

async def process_docs(docs_dir=settings.DOCS_DIR):
    docs = []
    print('\nLoading documents')

    files = [f for f in os.listdir(docs_dir) if f.endswith('.json')]
    if not files:
        print(f"No JSON files found in {docs_dir}")
        return []

    for filename in tqdm(files, desc="Processing files"):
        file_path = os.path.join(docs_dir, filename)
        doc_name = os.path.splitext(filename)[0]

        data = load_json_file(file_path)
        if not data or not isinstance(data, list):
            print(f"Invalid or empty JSON structure in {filename}")
            continue

        for item in data:
            attributes = {attr["label"]: attr["value"] for attr in item.get("attributes", [])}
            features = {feat["label"]: feat["value"] for feat in item.get("features", [])}
            variations = item.get("variations", [])
            category = item.get("category", "نامشخص")

            strict_category = category if category in [
                "کلاه کاسکت", "پوشاک موتورسواری", "لاستیک موتور سیکلت",
                "لوازم جانبی موتورسیکلت", "پروتکشن موتور سیکلت", "باکس موتور سیکلت",
                "لوازم کلاه کاسکت", "لوازم کلیک و طرح کلیک", "لوازم آیروکس و طرح آیروکس (NVX)",
                "سایر"
            ] else "نامشخص"

            price_numeric = item.get('price_numeric', 0)
            budget_range = normalize_budget_range(price_numeric)

            metadata = {
                'name': item.get('title', 'محصول ناشناس'),
                'price': item.get('price', 'نامشخص'),
                'price_numeric': price_numeric,
                'budget_range': budget_range,
                'brand': item.get('brand', 'نامشخص'),
                'category': strict_category,
                'link': item.get('url', ''),
                'stock': item.get('stock', 'نامشخص'),
                'attributes': attributes,
                'features': features,
                'tags': item.get('tags', []),
                'variations': variations,
                'product_id': item.get('product_id', ''),
                'image': item.get('image', ''),
                'description': item.get('description', '')
            }

            text_parts = []
            if 'title' in item:
                text_parts.append(f"نام محصول: {item['title']}")
            if 'price' in item:
                text_parts.append(f"قیمت: {item['price']}")
            if 'brand' in item:
                text_parts.append(f"برند: {item['brand']}")
            if strict_category != "نامشخص":
                text_parts.append(f"دسته‌بندی: {strict_category}")
            if features:
                text_parts.append("ویژگی‌ها:")
                for key, value in features.items():
                    text_parts.append(f"  - {key}: {value}")
            if variations:
                text_parts.append("سایزها و موجودی:")
                for var in variations:
                    text_parts.append(f"  - سایز: {var.get('size', 'نامشخص')}، موجودی: {var.get('stock', 'نامشخص')}")
            if 'description' in item and item['description']:
                text_parts.append(f"توضیحات: {item['description']}")
            if 'tags' in item and item['tags']:
                text_parts.append(f"تگ‌ها: {', '.join(item['tags'])}")
            if 'url' in item:
                text_parts.append(f"لینک محصول: {item['url']}")
            if 'image' in item:
                text_parts.append(f"تصویر: {item['image']}")

            text_block = "\n".join(text_parts)
            docs.append((item.get('title', 'محصول'), text_block, metadata))

    print(f'Loaded {len(docs)} documents')

    if not docs:
        print("No valid documents to process")
        return []

    chunks = []
    text_splitter = TextSplitter(chunk_size=512, chunk_overlap=150)
    print('\nSplitting documents into chunks')

    for doc_name, doc_text, metadata in tqdm(docs, desc="Splitting documents"):
        doc_id = str(uuid4())[:8]
        doc_chunks = text_splitter.split(doc_text)
        for chunk_idx, chunk_text in enumerate(doc_chunks):
            chunk = {
                'chunk_id': f'{doc_id}:{chunk_idx+1:04}',
                'text': chunk_text,
                'doc_name': doc_name,
                'vector': None,
                'metadata': metadata
            }
            chunks.append(chunk)
        print(f'{doc_name}: {len(doc_chunks)} chunks')

    chunk_sizes = [token_size(c['text']) for c in chunks]
    print(f'\nTotal chunks: {len(chunks)}')
    print(f'Min chunk size: {min(chunk_sizes)} tokens')
    print(f'Max chunk size: {max(chunk_sizes)} tokens')
    print(f'Average chunk size: {round(sum(chunk_sizes)/len(chunks))} tokens')

    vectors = []
    print('\nEmbedding chunks')
    with tqdm(total=len(chunks), desc="Embedding chunks") as pbar:
        for batch in batchify(chunks, batch_size=64):
            try:
                batch_vectors = await get_embeddings([chunk['text'] for chunk in batch])
                vectors.extend(batch_vectors)
                pbar.update(len(batch))
            except Exception as e:
                print(f"Error embedding batch: {e}")
                vectors.extend([None] * len(batch))
                pbar.update(len(batch))

    for chunk, vector in zip(chunks, vectors):
        chunk['vector'] = vector if vector else [0.0] * 1536  # Fallback vector

    return chunks

async def load_knowledge_base():
    async with get_redis() as rdb:
        print('Setting up Redis database')
        await setup_db(rdb)
        chunks = await process_docs()
        if chunks:
            print('\nAdding chunks to vector db')
            await add_chunks_to_vector_db(rdb, chunks)
            print('\nKnowledge base loaded')
        else:
            print('\nNo chunks to add to vector db')

def main():
    asyncio.run(load_knowledge_base())

if __name__ == '__main__':
    main()