from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ALLOW_ORIGINS: str = '*'
    OPENAI_API_KEY: str
    MODEL: str = "deepseek/deepseek-chat-v3.1:free"  # مدل پیش‌فرض DeepSeek
    EMBEDDING_MODEL: str = 'text-embedding-3-large'
    EMBEDDING_DIMENSIONS: int = 3072
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    DOCS_DIR: str = 'data/docs'
    EXPORT_DIR: str = 'data'
    VECTOR_SEARCH_TOP_K: int = 200
    POSTGRES_DSN: str
    DEEPSEEK_API_KEY: str  # کلید API DeepSeek
    DEEPSEEK_BASE_URL: str = "https://openrouter.ai/api/v1"  # آدرس پایه DeepSeek

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()