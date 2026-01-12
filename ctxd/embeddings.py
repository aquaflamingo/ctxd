"""
Embedding model wrapper for ctxd.

Provides a simple interface for generating embeddings using sentence-transformers,
with lazy loading and batch processing support.
"""

import logging
import threading
from typing import Optional
from sentence_transformers import SentenceTransformer

from .utils import retry_on_failure

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrapper around sentence-transformers for generating embeddings.

    Features:
    - Lazy model loading (only loads when first needed)
    - Automatic GPU detection with CPU fallback
    - Batch embedding generation
    - Model caching in memory
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: Optional[str] = None):
        """
        Initialize the embedding model.

        Args:
            model_name: Name of the sentence-transformers model to use
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name
        self.device = device
        self._model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None
        self._model_lock = threading.Lock()  # Thread safety for lazy loading

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the model on first access (thread-safe)."""
        if self._model is None:
            with self._model_lock:
                # Double-check pattern: another thread might have loaded it
                if self._model is None:
                    logger.info(f"Loading embedding model: {self.model_name}")
                    self._model = SentenceTransformer(self.model_name, device=self.device)
                    logger.info(f"Model loaded on device: {self._model.device}")
        return self._model

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            # Load model and get dimension from first encoding
            test_embedding = self.model.encode("test", show_progress_bar=False)
            self._dimension = len(test_embedding)
            logger.info(f"Embedding dimension: {self._dimension}")
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,  # Normalize for better similarity scores
        )
        return embedding.tolist()

    @retry_on_failure(max_attempts=3, delay=0.5, exceptions=(RuntimeError, OSError))
    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently with automatic retry on failure.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If all retry attempts fail
        """
        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,  # Show progress for large batches
            normalize_embeddings=True,
        )
        return [emb.tolist() for emb in embeddings]

    def __repr__(self) -> str:
        """String representation."""
        loaded = "loaded" if self._model is not None else "not loaded"
        return f"EmbeddingModel(model={self.model_name}, {loaded})"
