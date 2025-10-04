import tiktoken
from openai import AsyncOpenAI
from app.config import settings

# کلاینت OpenAI برای عملیات Embedding
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# کلاینت DeepSeek برای عملیات چت
deepseek_client = AsyncOpenAI(
    base_url=settings.DEEPSEEK_BASE_URL,
    api_key=settings.DEEPSEEK_API_KEY,
)

# انتخاب کلاینت مناسب بر اساس مدل
def get_client_for_model(model: str):
    if model.startswith("deepseek/"):
        return deepseek_client
    return openai_client

# انتخاب توکنایزر مناسب بر اساس مدل
def get_tokenizer_for_model(model: str):
    if model.startswith("deepseek/"):
        # DeepSeek از توکنایزر GPT-4 استفاده می‌کند
        return tiktoken.encoding_for_model("gpt-4")
    return tiktoken.encoding_for_model(model)

def token_size(text: str, model: str = settings.MODEL) -> int:
    """محاسبه تعداد توکن‌های متن بر اساس مدل انتخاب‌شده"""
    tokenizer = get_tokenizer_for_model(model)
    return len(tokenizer.encode(text))

# ========== Embeddings (با OpenAI) ==========

async def get_embedding(input: str, model: str = settings.EMBEDDING_MODEL, dimensions: int = settings.EMBEDDING_DIMENSIONS):
    """گرفتن یک embedding"""
    res = await openai_client.embeddings.create(input=input, model=model, dimensions=dimensions)
    return res.data[0].embedding

async def get_embeddings(inputs: list[str], model: str = settings.EMBEDDING_MODEL, dimensions: int = settings.EMBEDDING_DIMENSIONS):
    """گرفتن embedding برای لیست متن‌ها"""
    res = await openai_client.embeddings.create(input=inputs, model=model, dimensions=dimensions)
    return [d.embedding for d in res.data]

# ========== Chat (با DeepSeek) ==========

def chat_stream(messages: list[dict], model: str = settings.MODEL, temperature: float = 0.1, **kwargs):
    """
    استریم کردن پاسخ مدل (قطعه‌قطعه دریافت می‌کنی).
    """
    client = get_client_for_model(model)
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
    client = get_client_for_model(model)
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs
    )
    return resp.choices[0].message.content