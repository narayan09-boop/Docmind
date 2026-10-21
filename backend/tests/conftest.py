import sys
import os
import pytest
import pytest_asyncio
import httpx

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.main import app
from app.pipeline.retrieval import retrieval_pipe
from app.core.cache import semantic_cache

# Configure mock provider for fast, deterministic, offline testing
settings.EMBEDDING_PROVIDER = "mock"
settings.ENVIRONMENT = "testing"

@pytest.fixture(autouse=True)
def clean_state():
    """Isolate state between test runs."""
    retrieval_pipe.clear()
    semantic_cache.clear()
    yield
    retrieval_pipe.clear()
    semantic_cache.clear()

@pytest_asyncio.fixture
async def async_client():
    """Asynchronous HTTP test client using httpx.ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest.fixture
def sample_pdf_bytes():
    """Generates a minimal valid PDF byte stream for tests."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Operating revenue reached $4.2B in Q3.) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n310\n%%EOF"
