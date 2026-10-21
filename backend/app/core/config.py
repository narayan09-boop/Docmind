import os
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Production-grade application configuration with validation,
    environment discrimination, and security safeguards.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Core Application
    PROJECT_NAME: str = "DocMind Knowledge Copilot"
    VERSION: str = "1.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="development | staging | production | testing")
    LOG_LEVEL: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR | CRITICAL")

    # Security & Access Control
    API_KEY: Optional[str] = Field(default=None, description="Optional master API key for authenticating endpoints")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=15 * 1024 * 1024, description="Max PDF upload size (15MB default)")
    MAX_QUERY_LENGTH: int = Field(default=1000, description="Max allowed character length for incoming queries")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit requests per minute per IP")

    # Embedding & Reranker Architecture
    EMBEDDING_PROVIDER: str = Field(default="sentence-transformers", description="sentence-transformers | mock")
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2", description="HuggingFace model repository or name")
    EMBEDDING_DIMENSION: int = Field(default=384, description="Vector dimension size for index verification")
    RERANKER_MODEL_NAME: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    ENABLE_RERANKER: bool = Field(default=True, description="Toggle cross-encoder reranking step")
    RRF_K: int = Field(default=60, description="Smoothing constant for Reciprocal Rank Fusion")

    # LLM Inference Configuration
    LLM_PROVIDER: str = Field(default="local", description="openai | ollama | local (local uses deterministic grounded synthesis)")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="API Key for OpenAI provider")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, description="Custom base URL for OpenAI-compatible endpoints")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    LLM_MAX_TOKENS: int = Field(default=1024, ge=64, le=4096)
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0, ge=1.0, le=120.0)

    # Ingestion & Chunking
    DEFAULT_CHUNK_SIZE: int = Field(default=500, ge=100, le=4000)
    DEFAULT_CHUNK_OVERLAP: int = Field(default=50, ge=0, le=1000)
    SEMANTIC_SIMILARITY_PERCENTILE: float = Field(default=85.0, ge=50.0, le=99.0)

    # Semantic Cache & Persistence
    REDIS_URL: Optional[str] = Field(default=None, description="Optional Redis URI for persistent distributed cache")
    SEMANTIC_CACHE_ENABLED: bool = Field(default=True)
    SEMANTIC_CACHE_THRESHOLD: float = Field(default=0.90, ge=0.5, le=0.99)
    SEMANTIC_CACHE_TTL_SECONDS: int = Field(default=86400, ge=60)

    # Evaluation
    EVALUATION_DATASET_PATH: str = Field(
        default="docs/eval_benchmark_dataset.json",
        description="Path to default benchmark evaluation dataset"
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = {"development", "staging", "production", "testing"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid ENVIRONMENT '{v}'. Must be one of {valid_envs}")
        return v.lower()

    @model_validator(mode="after")
    def validate_production_constraints(self) -> "Settings":
        # Enforce security constraints in production
        if self.ENVIRONMENT == "production":
            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("CORS ALLOWED_ORIGINS cannot contain '*' wildcard in production environment.")
            if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required in production when LLM_PROVIDER is 'openai'.")
        return self

    def get_sanitized_dict(self) -> dict:
        """Returns configuration dictionary with secrets masked for safe logging."""
        data = self.model_dump()
        sensitive_keys = {"API_KEY", "OPENAI_API_KEY", "REDIS_URL"}
        for key in sensitive_keys:
            if data.get(key):
                data[key] = "******"
        return data

settings = Settings()
