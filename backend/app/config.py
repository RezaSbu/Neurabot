from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ALLOW_ORIGINS: str = '*'
    OPENAI_API_KEY: str
    MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = 'text-embedding-3-large'
    EMBEDDING_DIMENSIONS: int = 1024
    QDRANT_HOST: str = 'localhost'
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = 'products'
    QDRANT_CHAT_COLLECTION_NAME: str = 'chats'
    DOCS_DIR: str = 'data/docs'
    EXPORT_DIR: str = 'data'
    VECTOR_SEARCH_TOP_K: int = 10

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()