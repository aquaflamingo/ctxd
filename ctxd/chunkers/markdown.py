"""
Markdown chunking strategy.

Uses header-based chunking to split Markdown documents into sections.
"""

import re
import logging
from typing import Any

from .base import ChunkStrategy

logger = logging.getLogger(__name__)


class MarkdownChunker(ChunkStrategy):
    """
    Header-based chunking strategy for Markdown files.

    Splits Markdown documents by headers (# through ######), creating
    one chunk per section. Each chunk includes the header and all content
    until the next header of the same or higher level.
    """

    def chunk(self, content: str, path: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Split Markdown by header hierarchy.

        Args:
            content: The Markdown content
            path: File path for logging

        Returns:
            List of (chunk_text, metadata) tuples
        """
        if not content.strip():
            return []

        lines = content.split("\n")
        chunks = []

        current_chunk = []
        current_start = 1
        header_name = None

        for i, line in enumerate(lines, 1):
            # Check if line is a header (ATX style: # Header)
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                # Save previous chunk
                if current_chunk:
                    chunks.append(self._make_chunk(
                        current_chunk, current_start, i - 1, header_name
                    ))

                # Start new chunk
                header_name = header_match.group(2).strip()
                current_chunk = [line]
                current_start = i
            else:
                current_chunk.append(line)

        # Add final chunk
        if current_chunk:
            chunks.append(self._make_chunk(
                current_chunk, current_start, len(lines), header_name
            ))

        if chunks:
            logger.debug(f"Extracted {len(chunks)} sections from {path}")
        else:
            # No headers found - return whole file as one chunk
            logger.debug(f"No headers found in {path}, using single chunk")
            chunks = [(content, {
                "start_line": 1,
                "end_line": len(lines),
                "chunk_type": "block",
                "name": None,
            })]

        return chunks

    def _make_chunk(
        self,
        lines: list[str],
        start: int,
        end: int,
        name: str | None
    ) -> tuple[str, dict[str, Any]]:
        """
        Create chunk tuple from accumulated lines.

        Args:
            lines: Lines of content
            start: Starting line number
            end: Ending line number
            name: Section header name (without #)

        Returns:
            (chunk_text, metadata) tuple
        """
        text = "\n".join(lines)
        return (text, {
            "start_line": start,
            "end_line": end,
            "chunk_type": "section",
            "name": name,
        })
