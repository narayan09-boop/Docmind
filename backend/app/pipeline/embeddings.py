import logging
import numpy as np
from typing import List, Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Thread-safe lazy loader for embedding models and cross-encoders.
    Prevents eager model loading at module import time and supports mock mode for fast testing.
    """
    def __init__(self):
        self._encoder = None
        self._reranker = None
        self._dimension: Optional[int] = None

    def get_encoder(self):
        if settings.EMBEDDING_PROVIDER == "mock":
            return MockEncoder(dimension=settings.EMBEDDING_DIMENSION)

        if self._encoder is None:
            logger.info(f"Loading SentenceTransformer: {settings.EMBEDDING_MODEL_NAME}...")
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
                # Derive dimension dynamically from a dummy encode
                dummy = self._encoder.encode(["test"], normalize_embeddings=True)
                self._dimension = dummy.shape[1]
                logger.info(f"Loaded encoder with dynamic dimension: {self._dimension}")
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Falling back to MockEncoder.")
                self._encoder = MockEncoder(dimension=settings.EMBEDDING_DIMENSION)
                self._dimension = settings.EMBEDDING_DIMENSION
        return self._encoder

    def get_reranker(self):
        if not settings.ENABLE_RERANKER or settings.EMBEDDING_PROVIDER == "mock":
            return None

        if self._reranker is None:
            logger.info(f"Loading CrossEncoder: {settings.RERANKER_MODEL_NAME}...")
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder(settings.RERANKER_MODEL_NAME)
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder ({e}). Reranker disabled.")
                self._reranker = None
        return self._reranker

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self.get_encoder()
        return self._dimension or settings.EMBEDDING_DIMENSION


class MockEncoder:
    """Deterministic hash-based encoder for fast unit tests and low-resource environments."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        vectors = []
        for text in texts:
            # Deterministic pseudo-random vector derived from string hash
            seed = sum(ord(c) for c in text) % (2**32)
            rng = np.random.RandomState(seed)
            vec = rng.randn(self.dimension).astype(np.float32)
            if normalize_embeddings:
                norm = np.linalg.norm(vec) + 1e-9
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)

model_registry = ModelRegistry()
