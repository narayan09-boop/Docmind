import fitz  # PyMuPDF
import re
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class DocumentIngestionPipeline:
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model_name)

    def extract_document_elements(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Parses PDF layout, extracting text, coordinates, bounding boxes, and detects tables.
        """
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        elements = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1
            
            # Extract text blocks with layout bounding boxes [x0, y0, x1, y1]
            text_instances = page.get_text("blocks")
            for block in text_instances:
                # block: (x0, y0, x1, y1, text, block_no, block_type)
                text = block[4].strip()
                if not text:
                    continue
                
                # Check for tabular layout heuristic (tabs, pipes, aligned spaces)
                is_table = bool(re.search(r'(\t|\||\s{3,})', text)) and len(text.splitlines()) > 2
                
                elements.append({
                    "page": page_num,
                    "bbox": [round(block[0], 2), round(block[1], 2), round(block[2], 2), round(block[3], 2)],
                    "text": text,
                    "element_type": "table" if is_table else "text",
                    "filename": filename
                })

        doc.close()
        return elements

    def semantic_chunking(
        self, 
        elements: List[Dict[str, Any]], 
        breakpoint_percentile_threshold: float = 85.0
    ) -> List[Dict[str, Any]]:
        """
        Groups adjacent text blocks by semantic sentence similarity distance drops,
        retaining exact citation provenance (page and bounding boxes).
        """
        if not elements:
            return []

        # Split into sentence-level units with coordinate references
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
                        "element_type": elem["element_type"],
                        "filename": elem["filename"]
                    })

        if len(sentences_with_meta) <= 1:
            return sentences_with_meta

        # Compute embeddings for distance detection
        sentence_texts = [s["text"] for s in sentences_with_meta]
        embeddings = self.encoder.encode(sentence_texts, normalize_embeddings=True)

        # Compute cosine distances between adjacent sentences
        distances = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i + 1])
            distances.append(1.0 - sim)

        breakpoint_distance = np.percentile(distances, breakpoint_percentile_threshold) if distances else 0.5

        # Group sentences into semantic chunks
        chunks = []
        curr_chunk_sents = [sentences_with_meta[0]["text"]]
        curr_pages = {sentences_with_meta[0]["page"]}
        curr_bboxes = [sentences_with_meta[0]["bbox"]]
        curr_filename = sentences_with_meta[0]["filename"]
        has_table = sentences_with_meta[0]["element_type"] == "table"

        for i, dist in enumerate(distances):
            next_sent = sentences_with_meta[i + 1]
            if dist > breakpoint_distance or len(" ".join(curr_chunk_sents)) > 1200:
                # Flush current chunk
                chunks.append({
                    "chunk_id": len(chunks),
                    "content": " ".join(curr_chunk_sents),
                    "pages": sorted(list(curr_pages)),
                    "primary_page": list(curr_pages)[0],
                    "bboxes": curr_bboxes[:3], # retain primary bounding boxes for UI overlay
                    "has_table": has_table,
                    "filename": curr_filename
                })
                curr_chunk_sents = [next_sent["text"]]
                curr_pages = {next_sent["page"]}
                curr_bboxes = [next_sent["bbox"]]
                has_table = next_sent["element_type"] == "table"
            else:
                curr_chunk_sents.append(next_sent["text"])
                curr_pages.add(next_sent["page"])
                curr_bboxes.append(next_sent["bbox"])
                if next_sent["element_type"] == "table":
                    has_table = True

        # Append final chunk
        if curr_chunk_sents:
            chunks.append({
                "chunk_id": len(chunks),
                "content": " ".join(curr_chunk_sents),
                "pages": sorted(list(curr_pages)),
                "primary_page": list(curr_pages)[0],
                "bboxes": curr_bboxes[:3],
                "has_table": has_table,
                "filename": curr_filename
            })

        logger.info(f"Generated {len(chunks)} semantic chunks across {len(elements)} raw elements.")
        return chunks
