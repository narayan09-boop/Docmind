from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_hash: str
    filename: str
    content: str
    page_numbers: List[int]
    primary_page: int
    bboxes: List[List[float]] = Field(default_factory=list)
    element_type: str = "text"
    tenant_id: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)

class CitationInfo(BaseModel):
    citation_id: int
    filename: str
    page: int
    bboxes: List[List[float]] = Field(default_factory=list)
    snippet: str
    rerank_score: float

class QueryResult(BaseModel):
    query: str
    answer: str
    citations: List[CitationInfo] = Field(default_factory=list)
    is_cached: bool = False
    similarity_score: Optional[float] = None
    latency_ms: float
    tenant_id: str = "default"
