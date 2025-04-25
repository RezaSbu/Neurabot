# import os
# import asyncio
# from uuid import uuid4
# from tqdm import tqdm
# from pdfminer.high_level import extract_text
# from app.utils.splitter import TextSplitter
# from app.openai import get_embeddings, token_size
# from app.db import get_redis, setup_db, add_chunks_to_vector_db
# from app.config import settings

# def batchify(iterable, batch_size):
#     for i in range(0, len(iterable), batch_size):
#         yield iterable[i:i+batch_size]

# async def process_docs(docs_dir=settings.DOCS_DIR):
#     docs = []
#     print('\nLoading documents')
#     pdf_files = [f for f in os.listdir(docs_dir) if f.endswith('.pdf')]
#     for filename in tqdm(pdf_files):
#         file_path = os.path.join(docs_dir, filename)
#         text = extract_text(file_path)
#         doc_name = os.path.splitext(filename)[0]
#         docs.append((doc_name, text))
#     print(f'Loaded {len(docs)} PDF documents')

#     chunks = []
#     text_splitter = TextSplitter(chunk_size=512, chunk_overlap=150)
#     print('\nSplitting documents into chunks')
#     for doc_name, doc_text in docs:
#         doc_id = str(uuid4())[:8]
#         doc_chunks = text_splitter.split(doc_text)
#         for chunk_idx, chunk_text in enumerate(doc_chunks):
#             chunk = {
#                 'chunk_id': f'{doc_id}:{chunk_idx+1:04}',
#                 'text': chunk_text,
#                 'doc_name': doc_name,
#                 'vector': None
#             }
#             chunks.append(chunk)
#         print(f'{doc_name}: {len(doc_chunks)} chunks')
#     chunk_sizes = [token_size(c['text']) for c in chunks]
#     print(f'\nTotal chunks: {len(chunks)}')
#     print(f'Min chunk size: {min(chunk_sizes)} tokens')
#     print(f'Max chunk size: {max(chunk_sizes)} tokens')
#     print(f'Average chunk size: {round(sum(chunk_sizes)/len(chunks))} tokens')

#     vectors = []
#     print('\nEmbedding chunks')
#     with tqdm(total=len(chunks)) as pbar:
#         for batch in batchify(chunks, batch_size=64):
#             batch_vectors = await get_embeddings([chunk['text'] for chunk in batch])
#             vectors.extend(batch_vectors)
#             pbar.update(len(batch))

#     for chunk, vector in zip(chunks, vectors):
#         chunk['vector'] = vector
#     return chunks

# async def load_knowledge_base():
#     async with get_redis() as rdb:
#         print('Setting up Redis database')
#         await setup_db(rdb)
#         chunks = await process_docs()
#         print('\nAdding chunks to vector db')
#         await add_chunks_to_vector_db(rdb, chunks)
#         print('\nKnowledge base loaded')

# def main():
#     asyncio.run(load_knowledge_base())


# if __name__ == '__main__':
#     main()











import json
import os
import asyncio
from uuid import uuid4
from tqdm import tqdm
from pdfminer.high_level import extract_text
from app.utils.splitter import TextSplitter
from app.openai import get_embeddings, token_size
from app.db import get_redis, setup_db, add_chunks_to_vector_db
from app.config import settings

def batchify(iterable, batch_size):
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i+batch_size]

def extract_text_from_pdf(path):
    return extract_text(path)

def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def process_docs(docs_dir=settings.DOCS_DIR):
    docs = []
    print('\nLoading documents')

    files = [f for f in os.listdir(docs_dir) if f.endswith('.pdf') or f.endswith('.json')]

    for filename in tqdm(files):
        file_path = os.path.join(docs_dir, filename)
        ext = os.path.splitext(filename)[1].lower()

        doc_name = os.path.splitext(filename)[0]

        if ext == '.pdf':
            text = extract_text_from_pdf(file_path)
            docs.append((doc_name, text, {}))  # بدون metadata
        elif ext == '.json':
            data = load_json_file(file_path)
            if isinstance(data, list):
                for item in data:
                    metadata = {
                        'name': item.get('name', ''),
                        'price': item.get('price', ''),
                        'brand': item.get('specs', '').split('ساخت:')[-1].split('\n')[0].strip() if 'ساخت:' in item.get('specs', '') else '',
                        'category': item.get('category', ''),
                        'link': item.get('link', '')
                    }
                    text_block = "\n".join(f"{k}: {v}" for k, v in item.items())
                    docs.append((item.get("name", "محصول"), text_block, metadata))
        else:
            continue

    print(f'Loaded {len(docs)} documents')

    chunks = []
    text_splitter = TextSplitter(chunk_size=512, chunk_overlap=150)
    print('\nSplitting documents into chunks')

    for doc_name, doc_text, metadata in docs:
        doc_id = str(uuid4())[:8]
        doc_chunks = text_splitter.split(doc_text)
        for chunk_idx, chunk_text in enumerate(doc_chunks):
            chunk = {
                'chunk_id': f'{doc_id}:{chunk_idx+1:04}',
                'text': chunk_text,
                'doc_name': doc_name,
                'vector': None,
                'metadata': metadata  # 🎯 همینجا ذخیره‌ش کردیم
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
    with tqdm(total=len(chunks)) as pbar:
        for batch in batchify(chunks, batch_size=64):
            batch_vectors = await get_embeddings([chunk['text'] for chunk in batch])
            vectors.extend(batch_vectors)
            pbar.update(len(batch))

    for chunk, vector in zip(chunks, vectors):
        chunk['vector'] = vector

    return chunks

async def load_knowledge_base():
    async with get_redis() as rdb:
        print('Setting up Redis database')
        await setup_db(rdb)
        chunks = await process_docs()
        print('\nAdding chunks to vector db')
        await add_chunks_to_vector_db(rdb, chunks)
        print('\nKnowledge base loaded')

def main():
    asyncio.run(load_knowledge_base())

if __name__ == '__main__':
    main()


