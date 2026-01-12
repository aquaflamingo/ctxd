"""
MCP server for ctxd.

Exposes ctxd functionality to Claude Code and other MCP clients via the
Model Context Protocol.
"""

import argparse
import logging
import threading
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .config import Config
from .embeddings import EmbeddingModel
from .indexer import Indexer
from .models import IndexStats
from .store import VectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances (initialized in main)
store: Optional[VectorStore] = None
config: Optional[Config] = None

# Lazy-loaded components (Fix 1 & 3: Performance optimization)
_embeddings: Optional[EmbeddingModel] = None
_embeddings_config: Optional[str] = None
_indexer: Optional[Indexer] = None

# Initialize FastMCP server
mcp = FastMCP("ctxd")


def get_embeddings() -> EmbeddingModel:
    """
    Lazy-load the embedding model on first use.

    Returns:
        EmbeddingModel instance
    """
    global _embeddings, _embeddings_config
    if _embeddings is None:
        logger.info(f"Lazy-loading embedding model: {_embeddings_config}")
        _embeddings = EmbeddingModel(model_name=_embeddings_config)
    return _embeddings


def get_indexer() -> Indexer:
    """
    Lazy-load the indexer on first use (only needed for indexing operations).

    Returns:
        Indexer instance
    """
    global _indexer
    if _indexer is None:
        logger.info("Lazy-loading indexer")
        _indexer = Indexer(
            store=store,
            embeddings=get_embeddings(),
            config=config
        )
    return _indexer


@mcp.tool()
def ctx_search(
    query: str,
    limit: int = 10,
    # Existing filters
    file_filter: Optional[str] = None,
    branch: Optional[str] = None,
    # Phase 4: New filters
    extensions: Optional[list[str]] = None,
    directories: Optional[list[str]] = None,
    chunk_types: Optional[list[str]] = None,
    languages: Optional[list[str]] = None,
    # Phase 4: Search mode
    mode: Optional[str] = None,
    # Phase 4: Result enhancement
    expand_context: Optional[bool] = None,
    deduplicate: Optional[bool] = None,
) -> dict:
    """
    Search for code snippets semantically similar to the query.

    Args:
        query: Natural language search query
        limit: Maximum number of results to return (default: 10)
        file_filter: Optional glob pattern to filter files (e.g., "*.py", "src/**")
        branch: Optional git branch filter (e.g., "main", "develop")
        extensions: Filter by file extensions (e.g., [".py", ".js"])
        directories: Filter by directory prefixes (e.g., ["src/", "lib/"])
        chunk_types: Filter by chunk type (e.g., ["function", "class"])
        languages: Filter by language (e.g., ["python", "javascript"])
        mode: Search mode - "vector", "fts", or "hybrid" (default: from config)
        expand_context: Include surrounding lines from source files (default: from config)
        deduplicate: Remove overlapping chunks (default: from config)

    Returns:
        Dictionary with search results containing code chunks, file paths, and relevance scores
    """
    if not store:
        return {
            "error": "Index not initialized. Run ctx_index first.",
            "results": []
        }

    try:
        # Get config defaults
        search_mode = mode or config.get("search", "mode", default="hybrid")
        should_expand = expand_context if expand_context is not None \
                        else config.get("search", "expand_context", default=False)
        should_dedup = deduplicate if deduplicate is not None \
                       else config.get("search", "deduplicate", default=True)

        # Generate query embedding (needed for vector and hybrid modes)
        query_vector = None
        if search_mode in ["vector", "hybrid"]:
            query_vector = get_embeddings().embed_batch([query])[0]

        # Get search parameters from config
        min_score = config.get("search", "min_score", default=0.3)
        fts_weight = config.get("search", "fts_weight", default=0.5)

        # Search with all filters
        # Request more results if deduplication is enabled
        search_limit = limit * 2 if should_dedup else limit

        results = store.search(
            query_text=query,
            query_vector=query_vector,
            limit=search_limit,
            mode=search_mode,
            fts_weight=fts_weight,
            file_filter=file_filter,
            branch_filter=branch,
            extensions=extensions,
            directories=directories,
            chunk_types=chunk_types,
            languages=languages,
            min_score=min_score
        )

        # Enhance results
        from .result_enhancer import ResultEnhancer
        enhancer = ResultEnhancer()

        if should_dedup:
            overlap_threshold = config.get("search", "overlap_threshold", default=0.5)
            results = enhancer.deduplicate(results, overlap_threshold=overlap_threshold)

        # Apply recency ranking
        recency_weight = config.get("search", "recency_weight", default=0.1)
        results = enhancer.rerank_by_recency(results, recency_weight=recency_weight)

        # Trim to requested limit after deduplication
        results = results[:limit]

        # Expand context if requested
        if should_expand:
            lines_before = config.get("search", "context_lines_before", default=3)
            lines_after = config.get("search", "context_lines_after", default=3)
            results = enhancer.expand_context(
                results,
                lines_before=lines_before,
                lines_after=lines_after,
                project_root=config.project_root
            )

        # Format results for MCP response
        formatted_results = []
        for result in results:
            formatted_results.append({
                "path": result.chunk.path,
                "start_line": result.chunk.start_line,
                "end_line": result.chunk.end_line,
                "code": result.chunk.text,
                "score": round(result.score, 3),
                "language": result.chunk.language,
                "chunk_type": result.chunk.chunk_type,
                "name": result.chunk.name,
                "branch": result.chunk.branch,
            })

        logger.info(f"Search for '{query}' (mode={search_mode}) returned {len(formatted_results)} results")

        return {
            "query": query,
            "mode": search_mode,
            "count": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "results": []
        }


@mcp.tool()
def ctx_status() -> dict:
    """
    Get statistics about the indexed codebase.

    Returns:
        Dictionary with index statistics including file count, chunk count, languages, and last indexed time
    """
    if not store:
        return {
            "error": "Index not initialized",
            "stats": None
        }

    try:
        stats = store.get_stats()

        return {
            "total_files": stats.total_files,
            "total_chunks": stats.total_chunks,
            "total_size_mb": round(stats.total_size_bytes / 1024 / 1024, 2),
            "languages": stats.languages,
            "last_indexed": stats.last_indexed,
            "indexed": stats.total_chunks > 0
        }

    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        return {
            "error": str(e),
            "stats": None
        }


@mcp.tool()
def ctx_index(path: str = ".", force: bool = False, branch: Optional[str] = None) -> dict:
    """
    Index a file or directory.

    Args:
        path: Path to index relative to project root (default: ".")
        force: Force re-indexing of unchanged files (default: False)
        branch: Git branch to tag chunks with (auto-detected if not specified)

    Returns:
        Dictionary with indexing results and statistics
    """
    if not config:
        return {
            "error": "Config not initialized",
            "stats": None
        }

    try:
        # Resolve path relative to project root
        project_root = config.project_root
        target_path = (project_root / path).resolve()

        if not target_path.exists():
            return {
                "error": f"Path does not exist: {path}",
                "stats": None
            }

        logger.info(f"Indexing {target_path} (force={force}, branch={branch or 'auto-detect'})")

        # Perform indexing (lazy-load indexer on first use)
        stats = get_indexer().index_path(target_path, force=force, branch=branch)

        return {
            "path": str(path),
            "total_files": stats.total_files,
            "total_chunks": stats.total_chunks,
            "total_size_mb": round(stats.total_size_bytes / 1024 / 1024, 2),
            "languages": stats.languages,
            "last_indexed": stats.last_indexed,
        }

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "stats": None
        }


def initialize(project_root: Path) -> None:
    """
    Initialize the ctxd components.

    Args:
        project_root: Root directory of the project to index
    """
    global store, config, _embeddings_config

    # Load configuration
    config = Config(project_root)

    # Initialize components
    db_path = project_root / ".ctxd" / "data.lance"
    store = VectorStore(db_path)

    # Store embedding config for lazy loading (Fix 1: Performance optimization)
    # Don't create EmbeddingModel here - defer to first use
    _embeddings_config = config.get("embeddings", "model", default="all-MiniLM-L6-v2")

    # Don't create Indexer here either - defer to index operations (Fix 3: Performance optimization)
    # indexer will be lazy-loaded when needed

    # Warm model in background thread (Fix 5: Performance optimization)
    # This makes first search faster if user waits a few seconds before searching
    def warm_model():
        try:
            logger.debug("Background warming: loading embedding model")
            get_embeddings()  # Trigger lazy load
            logger.debug("Background warming: embedding model loaded")
        except Exception as e:
            logger.debug(f"Background warming failed (non-critical): {e}")

    threading.Thread(target=warm_model, daemon=True).start()

    logger.info(f"Initialized ctxd for project: {project_root}")


def main():
    """Entry point for the MCP server."""
    parser = argparse.ArgumentParser(
        description="ctxd MCP server for semantic code search"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Root directory of the project (default: current directory)"
    )

    args = parser.parse_args()

    # Initialize ctxd
    project_root = args.project_root.resolve()

    if not (project_root / ".ctxd").exists():
        logger.error(
            f"No .ctxd directory found in {project_root}. "
            f"Run 'ctxd init' first."
        )
        return

    initialize(project_root)

    # Run the MCP server (stdio transport)
    logger.info("Starting ctxd MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
