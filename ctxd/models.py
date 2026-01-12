"""
Data models for ctxd.

Defines Pydantic models and LanceDB schema for code chunks, search results,
and indexing statistics.
"""

import time
from typing import Optional
from pydantic import BaseModel, Field
from lancedb.pydantic import LanceModel, Vector


class CodeChunk(LanceModel):
    """
    LanceDB model for storing code chunks with embeddings.

    This model represents a semantically meaningful chunk of code/text
    that has been indexed for vector search.
    """
    vector: Vector(384) = Field(description="Embedding vector from sentence-transformers")
    text: str = Field(description="The actual code/text content")
    path: str = Field(description="File path relative to project root")
    start_line: int = Field(description="Starting line number in original file", ge=1)
    end_line: int = Field(description="Ending line number in original file", ge=1)
    chunk_type: str = Field(description="Type: function, class, block, or paragraph")
    name: Optional[str] = Field(default=None, description="Function/class name if applicable")
    language: str = Field(description="Detected programming language")
    file_hash: str = Field(description="SHA256 hash of source file for incremental indexing")
    indexed_at: float = Field(default_factory=time.time, description="Unix timestamp when indexed")
    branch: Optional[str] = Field(default=None, description="Git branch when indexed")


class ChunkMetadata(BaseModel):
    """Metadata about a code chunk."""
    path: str
    start_line: int
    end_line: int
    chunk_type: str
    name: Optional[str] = None
    language: str
    file_hash: str
    indexed_at: float = Field(default_factory=time.time)


class SearchResult(BaseModel):
    """A search result containing a code chunk and its similarity score."""
    chunk: CodeChunk
    score: float = Field(description="Similarity score (0-1)", ge=0, le=1)

    def __str__(self) -> str:
        """Format search result for display."""
        return (
            f"{self.chunk.path}:{self.chunk.start_line}-{self.chunk.end_line} "
            f"({self.score:.3f})\n{self.chunk.text[:100]}..."
        )


class IndexStats(BaseModel):
    """Statistics about the indexed codebase."""
    total_files: int = 0
    total_chunks: int = 0
    total_size_bytes: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    last_indexed: Optional[float] = None

    def __str__(self) -> str:
        """Format stats for display."""
        lines = [
            f"Total files: {self.total_files}",
            f"Total chunks: {self.total_chunks}",
            f"Index size: {self.total_size_bytes / 1024 / 1024:.2f} MB",
        ]
        if self.languages:
            lines.append("Languages:")
            for lang, count in sorted(self.languages.items(), key=lambda x: -x[1]):
                lines.append(f"  {lang}: {count}")
        if self.last_indexed:
            import datetime
            dt = datetime.datetime.fromtimestamp(self.last_indexed)
            lines.append(f"Last indexed: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)
