import tiktoken
from openai import AsyncOpenAI
from app.config import settings

# کلاینت OpenAI
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# توکنایزر برای شمارش توکن‌ها
tokenizer = tiktoken.encoding_for_model(settings.MODEL)


def token_size(text: str) -> int:
    """محاسبه تعداد توکن‌های متن بر اساس مدل انتخاب‌شده"""
    return len(tokenizer.encode(text))


# ========== Embeddings ==========

async def get_embedding(input: str, model: str = settings.EMBEDDING_MODEL, dimensions: int = settings.EMBEDDING_DIMENSIONS):
    """گرفتن یک embedding"""
    res = await client.embeddings.create(input=input, model=model, dimensions=dimensions)
    return res.data[0].embedding


async def get_embeddings(inputs: list[str], model: str = settings.EMBEDDING_MODEL, dimensions: int = settings.EMBEDDING_DIMENSIONS):
    """گرفتن embedding برای لیست متن‌ها"""
    res = await client.embeddings.create(input=inputs, model=model, dimensions=dimensions)
    return [d.embedding for d in res.data]


# ========== Chat ==========

def chat_stream(messages: list[dict], model: str = settings.MODEL, temperature: float = 0.1, **kwargs):
    """
    استریم کردن پاسخ مدل (قطعه‌قطعه دریافت می‌کنی).
    """
    return client.beta.chat.completions.stream(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs
    )


async def chat_completion(messages: list[dict], model: str = settings.MODEL, temperature: float = 0.1, **kwargs) -> str:
    """
    گرفتن پاسخ کامل از مدل (یکجا).
    """
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs
    )
    return resp.choices[0].message.content
