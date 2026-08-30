"""
Embedding service using sentence-transformers with fallback.
"""

from typing import List
from ..utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service to generate dense vector embeddings for text."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._failed = False

    def _get_model(self):
        if self._model is None and not self._failed:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info("embedding_model_loaded", model=self.model_name)
            except Exception as e:
                logger.warning("sentence_transformers_unavailable", error=str(e))
                self._failed = True
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Generate a dense embedding vector for text."""
        model = self._get_model()
        if model is not None:
            embedding = model.encode(text)
            return embedding.tolist()
        
        # Fallback dummy embedding (384 dimensions)
        import hashlib
        hash_val = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        vec = [(hash_val >> (i % 32) & 1) * 0.1 for i in range(384)]
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate dense embeddings for a batch of text."""
        return [self.embed_text(t) for t in texts]
