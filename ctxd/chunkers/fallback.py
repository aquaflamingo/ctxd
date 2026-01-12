"""
Fallback chunking strategy for unsupported file types.

Uses paragraph-based chunking with configurable size and overlap.
"""

import logging
from typing import Any
from .base import ChunkStrategy

logger = logging.getLogger(__name__)


class FallbackChunker(ChunkStrategy):
    """
    Paragraph-based chunking strategy for plain text and unsupported files.

    Splits content by paragraphs (double newlines) and ensures chunks
    don't exceed max_chunk_size with overlap between adjacent chunks.
    """

    def __init__(self, max_chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the fallback chunker.

        Args:
            max_chunk_size: Maximum chunk size in tokens (estimated by words)
            chunk_overlap: Number of tokens to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, content: str, path: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Split content into paragraph-based chunks.

        Args:
            content: The file content to chunk
            path: File path for logging

        Returns:
            List of (chunk_text, metadata) tuples
        """
        if not content.strip():
            return []

        lines = content.split("\n")
        paragraphs = self._split_into_paragraphs(content)

        if not paragraphs:
            # If no paragraphs found, treat entire content as one chunk
            return [(content, {
                "start_line": 1,
                "end_line": len(lines),
                "chunk_type": "block",
                "name": None,
            })]

        chunks = []
        current_line = 1

        for para in paragraphs:
            if not para.strip():
                continue

            para_lines = para.count("\n") + 1

            # Estimate tokens (rough approximation: 1 word ≈ 1.3 tokens)
            word_count = len(para.split())
            if word_count <= self.max_chunk_size:
                # Paragraph fits in one chunk
                chunks.append((para, {
                    "start_line": current_line,
                    "end_line": current_line + para_lines - 1,
                    "chunk_type": "paragraph",
                    "name": None,
                }))
            else:
                # Split large paragraph into smaller chunks
                sub_chunks = self._split_large_paragraph(para, current_line)
                chunks.extend(sub_chunks)

            current_line += para_lines

        logger.debug(f"Chunked {path} into {len(chunks)} chunks using fallback strategy")
        return chunks

    def _split_into_paragraphs(self, content: str) -> list[str]:
        """Split content by double newlines (paragraphs)."""
        # Split by double newlines, but preserve single newlines within paragraphs
        paragraphs = content.split("\n\n")
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_large_paragraph(
        self,
        paragraph: str,
        start_line: int
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Split a large paragraph into smaller chunks with overlap.

        Args:
            paragraph: The paragraph text
            start_line: Starting line number

        Returns:
            List of (chunk_text, metadata) tuples
        """
        words = paragraph.split()
        chunks = []
        i = 0
        current_line = start_line

        while i < len(words):
            # Take max_chunk_size words
            chunk_words = words[i:i + self.max_chunk_size]
            chunk_text = " ".join(chunk_words)

            # Count lines in this chunk (approximate)
            line_count = chunk_text.count("\n") + 1

            chunks.append((chunk_text, {
                "start_line": current_line,
                "end_line": current_line + line_count - 1,
                "chunk_type": "paragraph",
                "name": None,
            }))

            current_line += line_count

            # Move forward with overlap
            i += self.max_chunk_size - self.chunk_overlap

        return chunks
