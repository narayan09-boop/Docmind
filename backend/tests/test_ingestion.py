import pytest
from app.pipeline.ingestion import DocumentIngestionPipeline
from app.core.config import settings

def test_validate_empty_file():
    pipeline = DocumentIngestionPipeline()
    with pytest.raises(ValueError) as exc:
        pipeline.validate_file(b"", "empty.pdf")
    assert "is empty" in str(exc.value)

def test_validate_invalid_magic_bytes():
    pipeline = DocumentIngestionPipeline()
    with pytest.raises(ValueError) as exc:
        pipeline.validate_file(b"NOT_A_PDF_CONTENT", "fake.pdf")
    assert "valid PDF header signature" in str(exc.value)

def test_validate_oversized_file(monkeypatch):
    pipeline = DocumentIngestionPipeline()
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)
    with pytest.raises(ValueError) as exc:
        pipeline.validate_file(b"%PDF-1.4" + b"A" * 200, "large.pdf")
    assert "exceeds limit" in str(exc.value)

def test_content_hashing():
    pipeline = DocumentIngestionPipeline()
    h1 = pipeline.compute_hash(b"test-content-1")
    h2 = pipeline.compute_hash(b"test-content-1")
    h3 = pipeline.compute_hash(b"test-content-2")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64

def test_semantic_chunking_stable_ids(sample_pdf_bytes):
    pipeline = DocumentIngestionPipeline()
    elements = pipeline.extract_document_elements(sample_pdf_bytes, "sample.pdf")
    doc_hash = pipeline.compute_hash(sample_pdf_bytes)
    chunks = pipeline.semantic_chunking(elements, "sample.pdf", doc_hash, tenant_id="tenant_a")

    assert len(chunks) >= 1
    chunk = chunks[0]
    assert chunk.doc_hash == doc_hash
    assert chunk.chunk_id.startswith(doc_hash[:12])
    assert chunk.tenant_id == "tenant_a"
    assert "Operating revenue" in chunk.content
