import pytest
from pydantic import ValidationError
from app.core.config import Settings

def test_config_defaults():
    s = Settings()
    assert s.PROJECT_NAME == "DocMind Knowledge Copilot"
    assert s.DEFAULT_CHUNK_SIZE == 500
    assert s.SEMANTIC_CACHE_THRESHOLD == 0.90
    assert s.RATE_LIMIT_PER_MINUTE == 60

def test_config_invalid_environment():
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="invalid_env_name")

def test_production_wildcard_cors_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="production", ALLOWED_ORIGINS=["*"])
    assert "CORS ALLOWED_ORIGINS cannot contain '*'" in str(exc_info.value)

def test_production_missing_openai_key_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="production", LLM_PROVIDER="openai", OPENAI_API_KEY=None, ALLOWED_ORIGINS=["https://docmind.ai"])
    assert "OPENAI_API_KEY is required in production" in str(exc_info.value)

def test_secret_masking():
    s = Settings(API_KEY="super-secret-key-12345", OPENAI_API_KEY="sk-abcdef123456")
    sanitized = s.get_sanitized_dict()
    assert sanitized["API_KEY"] == "******"
    assert sanitized["OPENAI_API_KEY"] == "******"
