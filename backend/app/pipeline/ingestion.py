import fitz  # PyMuPDF
import re
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
import logging

from app.core.config import settings
from app.pipeline.models import DocumentChunk
from app.pipeline.embeddings import model_registry

logger = logging.getLogger(__name__)

class DocumentIngestionPipeline:
    """
    Production-grade multimodal document parsing and semantic chunking engine.
    Ensures safe parsing, content hashing, layout coordinates, and idempotent indexing.
    """
    def __init__(self):
        pass

    def validate_file(self, file_bytes: bytes, filename: str) -> None:
        """Enforces file size constraints and PDF file signature validation."""
        if not file_bytes:
            raise ValueError(f"Uploaded file '{filename}' is empty.")
            
        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValueError(
                f"File size {len(file_bytes) / (1024 * 1024):.2f}MB exceeds limit of "
                f"{settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.2f}MB."
            )

        # PDF Magic bytes check (%PDF-)
        if not file_bytes.startswith(b"%PDF"):
            raise ValueError(f"File '{filename}' does not have a valid PDF header signature.")

    def compute_hash(self, file_bytes: bytes) -> str:
        """Returns SHA-256 hash of document content for deduplication and provenance."""
        return hashlib.sha256(file_bytes).hexdigest()

    def extract_document_elements(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Extracts structured text blocks and layout coordinates [x0, y0, x1, y1] per page.
        """
        self.validate_file(file_bytes, filename)
        elements = []

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to parse PDF document '{filename}': {str(e)}")

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1
                text_instances = page.get_text("blocks")
                
                for block in text_instances:
                    # block: (x0, y0, x1, y1, text, block_no, block_type)
                    text = block[4].strip()
                    if not text:
                        continue
                    
                    # Tabular layout detection heuristic
                    is_table = bool(re.search(r'(\t|\||\s{3,})', text)) and len(text.splitlines()) > 2

                    elements.append({
                        "page": page_num,
                        "bbox": [round(block[0], 2), round(block[1], 2), round(block[2], 2), round(block[3], 2)],
                        "text": text,
                        "element_type": "table" if is_table else "text",
                        "filename": filename
                    })
        finally:
            doc.close()

        return elements

    def semantic_chunking(
        self, 
        elements: List[Dict[str, Any]], 
        filename: str,
        doc_hash: str,
        tenant_id: str = "default",
        breakpoint_percentile_threshold: Optional[float] = None
    ) -> List[DocumentChunk]:
        """
        Groups adjacent text blocks by semantic distance drops, preserving exact citation bounding boxes.
        """
        if not elements:
            return []

        threshold = breakpoint_percentile_threshold or settings.SEMANTIC_SIMILARITY_PERCENTILE

        # Flatten into sentence-level units with coordinate provenance
        sentences_with_meta = []
        for elem in elements:
            raw_sents = re.split(r'(?<=[.?!])\s+', elem["text"])
            for s in raw_sents:
                clean_s = s.strip()
                if len(clean_s) > 10:
                    sentences_with_meta.append({
                        "text": clean_s,
                        "page": elem["page"],
                        "bbox": elem["bbox"],
                        "element_type": elem["element_type"]
                    })

        if not sentences_with_meta:
            return []

        if len(sentences_with_meta) == 1:
            item = sentences_with_meta[0]
            return [
                DocumentChunk(
                    chunk_id=f"{doc_hash[:12]}_0",
                    doc_id=doc_hash[:16],
                    doc_hash=doc_hash,
                    filename=filename,
                    content=item["text"],
                    page_numbers=[item["page"]],
                    primary_page=item["page"],
                    bboxes=[item["bbox"]],
                    element_type=item["element_type"],
                    tenant_id=tenant_id
                )
            ]

        # Compute sentence embeddings
        encoder = model_registry.get_encoder()
        sentence_texts = [s["text"] for s in sentences_with_meta]
        embeddings = encoder.encode(sentence_texts, normalize_embeddings=True)

        # Distance gradient between consecutive sentences
        distances = []
        for i in range(len(embeddings) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i + 1]))
            distances.append(1.0 - sim)

        breakpoint_distance = float(np.percentile(distances, threshold)) if distances else 0.5

        chunks: List[DocumentChunk] = []
        curr_sents = [sentences_with_meta[0]["text"]]
        curr_pages = {sentences_with_meta[0]["page"]}
        curr_bboxes = [sentences_with_meta[0]["bbox"]]
        has_table = sentences_with_meta[0]["element_type"] == "table"

        for i, dist in enumerate(distances):
            next_sent = sentences_with_meta[i + 1]
            content_len = len(" ".join(curr_sents))

            if dist > breakpoint_distance or content_len > settings.DEFAULT_CHUNK_SIZE * 2:
                # Emit chunk
                chunk_obj = DocumentChunk(
                    chunk_id=f"{doc_hash[:12]}_{len(chunks)}",
                    doc_id=doc_hash[:16],
                    doc_hash=doc_hash,
                    filename=filename,
                    content=" ".join(curr_sents),
                    page_numbers=sorted(list(curr_pages)),
                    primary_page=list(curr_pages)[0],
                    bboxes=curr_bboxes[:3],
                    element_type="table" if has_table else "text",
                    tenant_id=tenant_id
                )
                chunks.append(chunk_obj)
                curr_sents = [next_sent["text"]]
                curr_pages = {next_sent["page"]}
                curr_bboxes = [next_sent["bbox"]]
                has_table = next_sent["element_type"] == "table"
            else:
                curr_sents.append(next_sent["text"])
                curr_pages.add(next_sent["page"])
                curr_bboxes.append(next_sent["bbox"])
                if next_sent["element_type"] == "table":
                    has_table = True

        if curr_sents:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_hash[:12]}_{len(chunks)}",
                    doc_id=doc_hash[:16],
                    doc_hash=doc_hash,
                    filename=filename,
                    content=" ".join(curr_sents),
                    page_numbers=sorted(list(curr_pages)),
                    primary_page=list(curr_pages)[0],
                    bboxes=curr_bboxes[:3],
                    element_type="table" if has_table else "text",
                    tenant_id=tenant_id
                )
            )

        logger.info(f"Ingestion: Parsed {len(chunks)} chunks for '{filename}' (hash: {doc_hash[:8]}).")
        return chunks
