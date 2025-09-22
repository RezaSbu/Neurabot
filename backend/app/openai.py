import tiktoken
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
tokenizer = tiktoken.encoding_for_model(settings.MODEL)

def token_size(text):
    """محاسبه تعداد توکن‌ها"""
    return len(tokenizer.encode(text))

async def get_embedding(input, model=None, dimensions=None):
    """دریافت امبدینگ برای یک متن"""
    if model is None:
        model = settings.EMBEDDING_MODEL
    if dimensions is None:
        dimensions = settings.EMBEDDING_DIMENSIONS
    
    # در اینجا می‌توان از مدل‌های کوانتایز شده استفاده کرد
    # برای مثال، با استفاده از کتابخانه‌هایی مانند ctransformers
    # اما برای سادگی، ما از OpenAI استفاده می‌کنیم
    res = await client.embeddings.create(input=input, model=model, dimensions=dimensions)
    return res.data[0].embedding

async def get_embeddings(input, model=None, dimensions=None):
    """دریافت امبدینگ برای چندین متن"""
    if model is None:
        model = settings.EMBEDDING_MODEL
    if dimensions is None:
        dimensions = settings.EMBEDDING_DIMENSIONS
    
    res = await client.embeddings.create(input=input, model=model, dimensions=dimensions)
    return [d.embedding for d in res.data]

def chat_stream(messages, model=None, temperature=0.1, **kwargs):
    """تکمیل چت با استریم"""
    if model is None:
        model = settings.MODEL
    
    # در اینجا می‌توان از مدل‌های کوانتایز شده استفاده کرد
    # برای مثال، با استفاده از کتابخانه‌هایی مانند ctransformers
    # اما برای سادگی، ما از OpenAI استفاده می‌کنیم
    return client.beta.chat.completions.stream(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs
    )