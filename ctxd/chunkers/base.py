"""
Base chunking strategy interface for ctxd.

Defines the abstract base class that all chunking strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class ChunkStrategy(ABC):
    """
    Abstract base class for chunking strategies.

    Different strategies can be implemented for different file types
    (e.g., AST-based chunking for code, paragraph-based for text).
    """

    @abstractmethod
    def chunk(self, content: str, path: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Split content into semantic chunks.

        Args:
            content: The file content to chunk
            path: File path (for context/metadata)

        Returns:
            List of (chunk_text, metadata) tuples where metadata contains:
            - start_line: Starting line number (1-indexed)
            - end_line: Ending line number (1-indexed)
            - chunk_type: Type of chunk ("function", "class", "block", "paragraph")
            - name: Optional name (function/class name if applicable)
        """
        pass
