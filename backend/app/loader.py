import json
import os
import asyncio
from uuid import uuid4
from tqdm import tqdm
from app.utils.splitter import TextSplitter
from app.openai import get_embeddings, token_size
from app.db import get_redis, setup_db, add_chunks_to_vector_db
from app.config import settings
from parsivar import Normalizer, FindStems
import csv

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

def load_csv_file(path):
    rows = []
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    except Exception as e:
        print(f"Error loading CSV file {path}: {e}")
    return rows

def normalize_budget_range(price_numeric):
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
    normalizer = Normalizer()
    stemmer = FindStems()
    print('\nLoading documents')

    files = [f for f in os.listdir(docs_dir) if f.endswith('.json') or f.endswith('.csv')]
    if not files:
        print(f"No data files found in {docs_dir}")
        return []

    for filename in tqdm(files, desc="Processing files"):
        file_path = os.path.join(docs_dir, filename)
        doc_name = os.path.splitext(filename)[0]

        if filename.endswith('.json'):
            data = load_json_file(file_path)
            if not data or not isinstance(data, list):
                print(f"Invalid or empty JSON structure in {filename}")
                continue
        else:
            csv_rows = load_csv_file(file_path)
            if not csv_rows:
                print(f"Empty CSV {filename}")
                continue
            # Map CSV rows to the expected item structure
            data = []
            for r in csv_rows:
                try:
                    # Attempt to parse complex fields if provided as JSON strings
                    def parse_jsonish(val):
                        if not val:
                            return []
                        try:
                            return json.loads(val)
                        except Exception:
                            return []

                    attributes = parse_jsonish(r.get('attributes'))
                    features = parse_jsonish(r.get('features'))
                    variations = parse_jsonish(r.get('variations'))
                    tags = parse_jsonish(r.get('tags'))

                    price_numeric = None
                    try:
                        price_numeric = float(r.get('price_numeric')) if r.get('price_numeric') not in [None, ''] else None
                    except Exception:
                        price_numeric = None

                    item = {
                        'title': r.get('title') or r.get('name') or '',
                        'price': r.get('price') or '',
                        'price_numeric': price_numeric or 0,
                        'brand': r.get('brand') or '',
                        'category': r.get('category') or 'نامشخص',
                        'url': r.get('url') or r.get('link') or '',
                        'stock': r.get('stock') or '',
                        'attributes': attributes,
                        'features': features,
                        'variations': variations,
                        'tags': tags,
                        'product_id': r.get('product_id') or r.get('id') or '',
                        'image': r.get('image') or r.get('image_url') or '',
                        'description': r.get('description') or '',
                    }
                    data.append(item)
                except Exception as e:
                    print(f"CSV row skipped due to error: {e}")

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

            # Normalize and stem features for cleaner text
            features_flat = "، ".join([f"{k}: {stemmer.convert_to_stem(normalizer.normalize(str(v)))}" for k, v in features.items()])
            sizes_flat = [v.get("size", "").upper() for v in variations if v.get("size")]

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
                'features_flat': features_flat.lower(),
                'sizes_flat': sizes_flat,
                'variations': variations,
                'tags': item.get('tags', []),
                'product_id': item.get('product_id', ''),
                'image': item.get('image', ''),
                'description': item.get('description', '')
            }

            # Semantic chunking: split into meaningful sections
            chunks = []
            doc_id = str(uuid4())[:8]

            # Chunk 1: Basic info (title, price, brand, category)
            basic_info = []
            if 'title' in item:
                basic_info.append(f"نام محصول: {normalizer.normalize(item['title'])}")
            if 'price' in item:
                basic_info.append(f"قیمت: {normalizer.normalize(item['price'])}")
            if 'brand' in item:
                basic_info.append(f"برند: {normalizer.normalize(item['brand'])}")
            if strict_category != "نامشخص":
                basic_info.append(f"دسته‌بندی: {strict_category}")
            if basic_info:
                chunks.append({
                    'chunk_id': f'{doc_id}:0001',
                    'text': "\n".join(basic_info),
                    'doc_name': doc_name,
                    'vector': None,
                    'metadata': metadata
                })

            # Chunk 2: Features
            if features:
                feature_text = ["ویژگی‌ها:"]
                for key, value in features.items():
                    feature_text.append(f"  - {key}: {stemmer.convert_to_stem(normalizer.normalize(str(value)))}")
                chunks.append({
                    'chunk_id': f'{doc_id}:0002',
                    'text': "\n".join(feature_text),
                    'doc_name': doc_name,
                    'vector': None,
                    'metadata': metadata
                })

            # Chunk 3: Description
            if 'description' in item and item['description']:
                chunks.append({
                    'chunk_id': f'{doc_id}:0003',
                    'text': f"توضیحات: {normalizer.normalize(item['description'])}",
                    'doc_name': doc_name,
                    'vector': None,
                    'metadata': metadata
                })

            # Chunk 4: Variations and other metadata
            if variations or 'tags' in item or 'url' in item or 'image' in item:
                extra_info = []
                if variations:
                    extra_info.append("سایزها و موجودی:")
                    for var in variations:
                        extra_info.append(f"  - سایز: {var.get('size', 'نامشخص')}، موجودی: {var.get('stock', 'نامشخص')}")
                if 'tags' in item and item['tags']:
                    extra_info.append(f"تگ‌ها: {', '.join(item['tags'])}")
                if 'url' in item:
                    extra_info.append(f"لینک محصول: {item['url']}")
                if 'image' in item:
                    extra_info.append(f"تصویر: {item['image']}")
                if extra_info:
                    chunks.append({
                        'chunk_id': f'{doc_id}:0004',
                        'text': "\n".join(extra_info),
                        'doc_name': doc_name,
                        'vector': None,
                        'metadata': metadata
                    })

            docs.extend(chunks)

    print(f'Loaded {len(docs)} chunks')

    if not docs:
        print("No valid chunks to process")
        return []

    text_splitter = TextSplitter(chunk_size=256, chunk_overlap=50)  # Smaller size, 20% overlap
    refined_chunks = []
    print('\nRefining chunks for size constraints')

    for chunk in tqdm(docs, desc="Refining chunks"):
        doc_chunks = text_splitter.split(chunk['text'])
        for idx, sub_chunk_text in enumerate(doc_chunks):
            refined_chunks.append({
                'chunk_id': f"{chunk['chunk_id'].split(':')[0]}:{idx+1:04}",
                'text': sub_chunk_text,
                'doc_name': chunk['doc_name'],
                'vector': None,
                'metadata': chunk['metadata']
            })

    chunk_sizes = [token_size(c['text']) for c in refined_chunks]
    print(f'\nTotal chunks: {len(refined_chunks)}')
    print(f'Min chunk size: {min(chunk_sizes)} tokens')
    print(f'Max chunk size: {max(chunk_sizes)} tokens')
    print(f'Average chunk size: {round(sum(chunk_sizes)/len(refined_chunks))} tokens')

    vectors = []
    print('\nEmbedding chunks')
    with tqdm(total=len(refined_chunks), desc="Embedding chunks") as pbar:
        for batch in batchify(refined_chunks, batch_size=128):
            try:
                batch_vectors = await get_embeddings([chunk['text'] for chunk in batch])
                vectors.extend(batch_vectors)
                pbar.update(len(batch))
            except Exception as e:
                print(f"Error embedding batch: {e}")
                vectors.extend([None] * len(batch))
                pbar.update(len(batch))

    for chunk, vector in zip(refined_chunks, vectors):
        chunk['vector'] = vector if vector else [0.0] * settings.EMBEDDING_DIMENSIONS

    return refined_chunks

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