"""
ctxd - Local-first semantic code search daemon for AI coding assistants.

This package provides:
- Vector-based code search using LanceDB and sentence-transformers
- Incremental indexing with file watching
- Git-aware indexing with .gitignore support
- Language-aware chunking (TreeSitter for Python, fallback for others)
- MCP integration (Phase 2)
"""

from .models import CodeChunk, SearchResult, IndexStats, ChunkMetadata
from .config import Config
from .embeddings import EmbeddingModel
from .store import VectorStore
from .indexer import Indexer
from .watcher import FileWatcher
from .chunkers import ChunkStrategy, TreeSitterChunker, FallbackChunker

__version__ = "0.2.0"

__all__ = [
    # Models
    "CodeChunk",
    "SearchResult",
    "IndexStats",
    "ChunkMetadata",
    # Core components
    "Config",
    "EmbeddingModel",
    "VectorStore",
    "Indexer",
    "FileWatcher",
    # Chunkers
    "ChunkStrategy",
    "TreeSitterChunker",
    "FallbackChunker",
]
