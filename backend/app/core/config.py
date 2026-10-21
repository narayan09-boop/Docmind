from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocMind Knowledge Copilot"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Embedding & Reranker models
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # LLM Provider configuration
    OPENAI_API_KEY: Optional[str] = "mock-or-key"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Cache & Database settings
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    SEMANTIC_CACHE_THRESHOLD: float = 0.92
    
    # Chunking defaults
    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 50
    SEMANTIC_SIMILARITY_PERCENTILE: float = 85.0

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
