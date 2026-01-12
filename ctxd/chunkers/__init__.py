"""
Chunking strategies for ctxd.

Provides different strategies for splitting code into semantic chunks:
- TreeSitterChunker: AST-based chunking for Python, JS/TS, Go
- MarkdownChunker: Header-based chunking for Markdown
- FallbackChunker: Paragraph-based chunking for other files
"""

from .base import ChunkStrategy
from .treesitter import TreeSitterChunker
from .markdown import MarkdownChunker
from .fallback import FallbackChunker

__all__ = [
    "ChunkStrategy",
    "TreeSitterChunker",
    "MarkdownChunker",
    "FallbackChunker",
]
