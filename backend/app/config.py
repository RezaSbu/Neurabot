from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ALLOW_ORIGINS: str = '*'
    OPENAI_API_KEY: str
    MODEL: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.05  # More consistent responses
    EMBEDDING_MODEL: str = 'text-embedding-3-large'
    EMBEDDING_DIMENSIONS: int = 3072
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    DOCS_DIR: str = 'data/docs'
    EXPORT_DIR: str = 'data'
    
    # Enhanced search parameters
    VECTOR_SEARCH_TOP_K: int = 20  # More candidates for reranking
    HYBRID_SEARCH_ALPHA: float = 0.7  # Fine-tuned balance
    RERANK_TOP_K: int = 12
    
    # Expert assistant parameters
    MAX_TOOL_CALLS: int = 15  # Allow complex multi-step reasoning
    CONTEXT_WINDOW_UTILIZATION: float = 0.8  # Use more context
    HISTORY_SIZE: int = 40  # Longer conversation memory
    
    # Business logic parameters
    CROSS_SELL_THRESHOLD: float = 0.3
    UPSELL_MAX_PERCENTAGE: float = 30.0
    STOCK_ALERT_THRESHOLD: int = 5
    COMPATIBILITY_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Response quality parameters
    MIN_PRODUCTS_FOR_COMPARISON: int = 2
    MAX_PRODUCTS_FOR_COMPARISON: int = 5
    COMPLEMENTARY_PRODUCTS_LIMIT: int = 3
    
    POSTGRES_DSN: str

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()