import pytest
from app.pipeline.retrieval import HybridRetrievalPipeline
from app.pipeline.models import DocumentChunk

def test_idempotent_indexing():
    pipeline = HybridRetrievalPipeline()
    c1 = DocumentChunk(
        chunk_id="chk_1",
        doc_id="doc_1",
        doc_hash="h1",
        filename="report.pdf",
        content="Enterprise cloud computing revenue surged by 45%.",
        page_numbers=[1],
        primary_page=1,
        tenant_id="tenant_x"
    )

    added_first = pipeline.index_chunks([c1], tenant_id="tenant_x")
    assert added_first == 1
    assert pipeline.get_chunk_count("tenant_x") == 1

    # Re-indexing the exact same chunk should be a no-op
    added_second = pipeline.index_chunks([c1], tenant_id="tenant_x")
    assert added_second == 0
    assert pipeline.get_chunk_count("tenant_x") == 1

def test_tenant_retrieval_isolation():
    pipeline = HybridRetrievalPipeline()
    chunk_a = DocumentChunk(
        chunk_id="chk_a",
        doc_id="doc_a",
        doc_hash="ha",
        filename="secret_a.pdf",
        content="Tenant A confidential research findings.",
        page_numbers=[1],
        primary_page=1,
        tenant_id="tenant_a"
    )
    chunk_b = DocumentChunk(
        chunk_id="chk_b",
        doc_id="doc_b",
        doc_hash="hb",
        filename="secret_b.pdf",
        content="Tenant B confidential financial projections.",
        page_numbers=[1],
        primary_page=1,
        tenant_id="tenant_b"
    )

    pipeline.index_chunks([chunk_a], tenant_id="tenant_a")
    pipeline.index_chunks([chunk_b], tenant_id="tenant_b")

    # Search as Tenant A
    citations_a, _ = pipeline.search("confidential", tenant_id="tenant_a")
    assert len(citations_a) == 1
    assert citations_a[0].filename == "secret_a.pdf"

    # Search as Tenant B
    citations_b, _ = pipeline.search("confidential", tenant_id="tenant_b")
    assert len(citations_b) == 1
    assert citations_b[0].filename == "secret_b.pdf"

    # Search as unknown Tenant C
    citations_c, _ = pipeline.search("confidential", tenant_id="tenant_c")
    assert len(citations_c) == 0

def test_empty_search_graceful():
    pipeline = HybridRetrievalPipeline()
    citations, emb = pipeline.search("query", tenant_id="empty_tenant")
    assert citations == []
    assert len(emb) > 0
