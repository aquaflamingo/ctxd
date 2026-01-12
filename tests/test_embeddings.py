"""
Unit tests for the embeddings module.

Tests the EmbeddingModel wrapper around sentence-transformers.
"""

import pytest
from ctxd.embeddings import EmbeddingModel


def test_embedding_model_lazy_loading():
    """Test that the model is lazy-loaded on first use."""
    model = EmbeddingModel()
    assert model._model is None  # Not loaded yet

    # Access the model property to trigger loading
    _ = model.model
    assert model._model is not None  # Now loaded


def test_embed_text_single():
    """Test embedding a single text."""
    model = EmbeddingModel()
    text = "This is a test sentence."

    embedding = model.embed_text(text)

    assert isinstance(embedding, list)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 produces 384-dim embeddings
    assert all(isinstance(x, float) for x in embedding)


def test_embed_text_returns_normalized():
    """Test that embeddings are normalized."""
    model = EmbeddingModel()
    text = "Test normalization"

    embedding = model.embed_text(text)

    # Check that the L2 norm is approximately 1 (normalized)
    import math
    norm = math.sqrt(sum(x * x for x in embedding))
    assert abs(norm - 1.0) < 0.01  # Allow small floating point error


def test_embed_batch():
    """Test embedding multiple texts in a batch."""
    model = EmbeddingModel()
    texts = [
        "First sentence",
        "Second sentence",
        "Third sentence",
    ]

    embeddings = model.embed_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 384 for emb in embeddings)
    assert all(isinstance(x, float) for emb in embeddings for x in emb)


def test_embed_batch_empty():
    """Test that empty batch returns empty list."""
    model = EmbeddingModel()
    embeddings = model.embed_batch([])
    assert embeddings == []


def test_embedding_dimension_property():
    """Test the dimension property."""
    model = EmbeddingModel()
    dim = model.dimension

    assert dim == 384
    assert model._dimension == 384  # Cached


def test_different_texts_produce_different_embeddings():
    """Test that different texts produce different embeddings."""
    model = EmbeddingModel()

    emb1 = model.embed_text("Python programming")
    emb2 = model.embed_text("JavaScript development")

    # Embeddings should be different
    assert emb1 != emb2


def test_similar_texts_have_high_similarity():
    """Test that similar texts have high cosine similarity."""
    model = EmbeddingModel()

    emb1 = model.embed_text("machine learning algorithms")
    emb2 = model.embed_text("algorithms for machine learning")

    # Compute cosine similarity (dot product since vectors are normalized)
    similarity = sum(a * b for a, b in zip(emb1, emb2))

    # Similar texts should have high similarity (> 0.7)
    assert similarity > 0.7


def test_model_repr():
    """Test the string representation."""
    model = EmbeddingModel()
    repr_str = repr(model)

    assert "EmbeddingModel" in repr_str
    assert "all-MiniLM-L6-v2" in repr_str
    assert "not loaded" in repr_str

    # Access model to load it
    _ = model.model
    repr_str = repr(model)
    assert "loaded" in repr_str
