"""
Vector store abstraction for ctxd.

Provides a clean interface over LanceDB for storing and searching code chunks.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional
from functools import lru_cache
import lancedb
from lancedb.table import Table

from .models import CodeChunk, SearchResult, IndexStats

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Abstraction over LanceDB for vector storage and retrieval.

    Features:
    - Initialize/create database and table
    - Add chunks with automatic deduplication
    - Semantic search with filtering
    - File hash tracking for incremental indexing
    - Statistics and metadata queries
    """

    def __init__(self, db_path: Path, table_name: str = "code_chunks", config: Optional[dict] = None):
        """
        Initialize the vector store.

        Args:
            db_path: Path to the LanceDB database directory
            table_name: Name of the table to use
            config: Optional configuration dictionary for caching and optimization
        """
        self.db_path = db_path
        self.table_name = table_name
        self._db: Optional[lancedb.DBConnection] = None
        self._table: Optional[Table] = None

        # Ensure parent directory exists (backward compatibility)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Query optimization settings (Phase 6) - backward compatible defaults
        if config:
            self.cache_enabled = config.get("cache_enabled", True) if isinstance(config, dict) else True
            self.cache_size = config.get("cache_size", 100) if isinstance(config, dict) else 100
            self.nprobes = config.get("nprobes", 20) if isinstance(config, dict) else 20
        else:
            self.cache_enabled = True
            self.cache_size = 100
            self.nprobes = 20

        # Create LRU cache for queries (Phase 6)
        if self.cache_enabled:
            self._cached_search = lru_cache(maxsize=self.cache_size)(self._execute_search_impl)

    @property
    def db(self) -> lancedb.DBConnection:
        """Lazy-load the database connection."""
        if self._db is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self.db_path))
            logger.info(f"Connected to LanceDB at {self.db_path}")
        return self._db

    @property
    def table(self) -> Table:
        """Get or create the code chunks table."""
        if self._table is None:
            table_names = self.db.table_names()
            if self.table_name in table_names:
                self._table = self.db.open_table(self.table_name)
                logger.debug(f"Opened existing table: {self.table_name}")
            else:
                # Create table with schema
                # Handle race condition: multiple workers may try to create simultaneously
                try:
                    self._table = self.db.create_table(
                        self.table_name,
                        schema=CodeChunk,
                        mode="create"
                    )
                    # Create FTS index for BM25 search
                    try:
                        self._table.create_fts_index("text", replace=True)
                        logger.info(f"Created FTS index on 'text' column for {self.table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to create FTS index: {e}")
                    logger.info(f"Created new table: {self.table_name}")
                except Exception as e:
                    # Table was created by another worker, open it instead
                    if "already exists" in str(e):
                        logger.debug(f"Table {self.table_name} was created by another worker, opening it")
                        self._table = self.db.open_table(self.table_name)
                    else:
                        raise
        return self._table

    def add_chunks(self, chunks: list[CodeChunk]) -> None:
        """
        Add code chunks to the store.

        Args:
            chunks: List of CodeChunk objects to add
        """
        if not chunks:
            return

        try:
            # Convert to dict format for LanceDB
            data = [chunk.model_dump() for chunk in chunks]
            self.table.add(data)
            logger.info(f"Added {len(chunks)} chunks to {self.table_name}")

            # Invalidate search cache since index has changed (Phase 6)
            self.clear_cache()

        except Exception as e:
            logger.error(f"Failed to add chunks: {e}")
            raise

    def clear_cache(self) -> None:
        """Clear the query cache (Phase 6)."""
        if self.cache_enabled and hasattr(self, '_cached_search'):
            try:
                self._cached_search.cache_clear()
                logger.debug("Search cache cleared")
            except AttributeError:
                pass

    def _generate_cache_key(
        self,
        query_text: Optional[str],
        query_vector: Optional[list[float]],
        limit: int,
        mode: str,
        **filters
    ) -> str:
        """
        Generate a cache key for search parameters.

        Args:
            query_text: Text query
            query_vector: Vector query (only use first few values for key)
            limit: Result limit
            mode: Search mode
            **filters: Additional filter parameters

        Returns:
            SHA256 hash of parameters
        """
        # Build cache key from parameters
        key_parts = [
            f"mode={mode}",
            f"limit={limit}",
            f"text={query_text or ''}",
        ]

        # Only include vector prefix for cache key (first 5 values)
        if query_vector:
            vector_prefix = str(query_vector[:5])
            key_parts.append(f"vector_prefix={vector_prefix}")

        # Add all filters
        for key, value in sorted(filters.items()):
            if value is not None:
                key_parts.append(f"{key}={value}")

        # Generate hash
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def search(
        self,
        query_vector: Optional[list[float]] = None,
        limit: int = 10,
        file_filter: Optional[str] = None,
        branch_filter: Optional[str] = None,
        min_score: float = 0.0,
        # Phase 4: New parameters
        query_text: Optional[str] = None,
        mode: Optional[str] = None,
        fts_weight: float = 0.5,
        extensions: Optional[list[str]] = None,
        directories: Optional[list[str]] = None,
        chunk_types: Optional[list[str]] = None,
        languages: Optional[list[str]] = None,
        # Phase 6: Cache control
        use_cache: bool = True,
    ) -> list[SearchResult]:
        """
        Search for similar code chunks with multiple modes.

        Args:
            query_vector: Query embedding vector for vector mode (backward compatible)
            limit: Maximum number of results
            file_filter: Optional glob pattern to filter files (backward compatible)
            branch_filter: Optional git branch filter (backward compatible)
            min_score: Minimum similarity score (0-1, backward compatible)
            query_text: Text query for hybrid/FTS mode (Phase 4)
            mode: Search mode - "vector", "fts", or "hybrid" (Phase 4, default: auto-detect)
            fts_weight: Weight for BM25 in hybrid mode (Phase 4, 0.0-1.0, default: 0.5)
            extensions: Filter by file extensions (Phase 4, e.g., [".py", ".js"])
            directories: Filter by directory prefixes (Phase 4, e.g., ["src/", "lib/"])
            chunk_types: Filter by chunk type (Phase 4, e.g., ["function", "class"])
            languages: Filter by language (Phase 4, e.g., ["python", "javascript"])
            use_cache: Whether to use query cache (Phase 6, default: True)

        Returns:
            List of SearchResult objects ordered by relevance
        """
        try:
            # Auto-detect mode if not specified
            if mode is None:
                if query_text and query_vector:
                    mode = "hybrid"
                elif query_vector:
                    mode = "vector"
                elif query_text:
                    mode = "fts"
                else:
                    raise ValueError("Either query_text or query_vector must be provided")

            # Validate inputs based on mode
            if mode == "vector" and query_vector is None:
                raise ValueError("query_vector required for vector mode")
            if mode in ["fts", "hybrid"] and query_text is None:
                raise ValueError("query_text required for fts/hybrid mode")

            # Check cache if enabled
            if self.cache_enabled and use_cache and hasattr(self, '_cached_search'):
                cache_key = self._generate_cache_key(
                    query_text, query_vector, limit, mode,
                    file_filter=file_filter, branch_filter=branch_filter,
                    fts_weight=fts_weight, extensions=extensions,
                    directories=directories, chunk_types=chunk_types,
                    languages=languages, min_score=min_score
                )
                try:
                    results = self._cached_search(
                        cache_key, query_text, query_vector, mode, limit, fts_weight,
                        file_filter, branch_filter, extensions, directories,
                        chunk_types, languages, min_score
                    )
                    logger.debug(f"Search cache hit for key={cache_key[:8]}...")
                    return results
                except TypeError:
                    # Cache miss or unhashable type, fall through
                    pass

            # Execute search without cache
            if mode == "vector":
                results = self._search_vector(query_vector, limit, file_filter, branch_filter,
                                             extensions, directories, chunk_types, languages)
            elif mode == "fts":
                results = self._search_fts(query_text, limit, file_filter, branch_filter,
                                          extensions, directories, chunk_types, languages)
            elif mode == "hybrid":
                results = self._search_hybrid(query_text, query_vector, limit, fts_weight,
                                             file_filter, branch_filter, extensions, directories,
                                             chunk_types, languages)
            else:
                raise ValueError(f"Invalid search mode: {mode}. Use 'vector', 'fts', or 'hybrid'")

            # Apply min_score filter
            results = self._post_filter(results, min_score)

            logger.debug(f"Search (mode={mode}) returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def _execute_search_impl(
        self,
        cache_key: str,
        query_text: Optional[str],
        query_vector: Optional[list[float]],
        mode: str,
        limit: int,
        fts_weight: float,
        file_filter: Optional[str],
        branch_filter: Optional[str],
        extensions: Optional[tuple],
        directories: Optional[tuple],
        chunk_types: Optional[tuple],
        languages: Optional[tuple],
        min_score: float,
    ) -> list[SearchResult]:
        """
        Internal cached search implementation.
        This method is wrapped with lru_cache for performance.
        """
        # Route to appropriate search method
        if mode == "vector":
            results = self._search_vector(query_vector, limit, file_filter, branch_filter,
                                         extensions, directories, chunk_types, languages)
        elif mode == "fts":
            results = self._search_fts(query_text, limit, file_filter, branch_filter,
                                      extensions, directories, chunk_types, languages)
        elif mode == "hybrid":
            results = self._search_hybrid(query_text, query_vector, limit, fts_weight,
                                         file_filter, branch_filter, extensions, directories,
                                         chunk_types, languages)
        else:
            raise ValueError(f"Invalid search mode: {mode}")

        # Apply min_score filter
        return self._post_filter(results, min_score)

    def _search_vector(
        self,
        query_vector: list[float],
        limit: int,
        file_filter: Optional[str],
        branch_filter: Optional[str],
        extensions: Optional[list[str]],
        directories: Optional[list[str]],
        chunk_types: Optional[list[str]],
        languages: Optional[list[str]]
    ) -> list[SearchResult]:
        """Perform pure vector similarity search."""
        query = self.table.search(query_vector).limit(limit)
        query = self._apply_filters(query, file_filter, branch_filter, extensions,
                                    directories, chunk_types, languages)
        results = query.to_list()
        return self._convert_results(results, score_type="distance")

    def _search_fts(
        self,
        query_text: str,
        limit: int,
        file_filter: Optional[str],
        branch_filter: Optional[str],
        extensions: Optional[list[str]],
        directories: Optional[list[str]],
        chunk_types: Optional[list[str]],
        languages: Optional[list[str]]
    ) -> list[SearchResult]:
        """Perform keyword-only BM25 search."""
        try:
            # Use fts_search method for full-text search
            query = self.table.search(query_text, query_type="fts").limit(limit)
            query = self._apply_filters(query, file_filter, branch_filter, extensions,
                                        directories, chunk_types, languages)
            results = query.to_list()
            return self._convert_results(results, score_type="fts")
        except (ValueError, AttributeError) as e:
            # Fall back to vector search if FTS is not available
            logger.warning(f"FTS search not available ({e}), falling back to simple text matching")
            # Fallback: just return empty results since we can't do proper FTS without setup
            return []

    def _search_hybrid(
        self,
        query_text: str,
        query_vector: Optional[list[float]],
        limit: int,
        fts_weight: float,
        file_filter: Optional[str],
        branch_filter: Optional[str],
        extensions: Optional[list[str]],
        directories: Optional[list[str]],
        chunk_types: Optional[list[str]],
        languages: Optional[list[str]]
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector and FTS."""
        try:
            # Use LanceDB's hybrid search with RRF reranking
            query = self.table.search(query_text, query_type="hybrid").limit(limit)
            query = self._apply_filters(query, file_filter, branch_filter, extensions,
                                        directories, chunk_types, languages)
            results = query.to_list()
            return self._convert_results(results, score_type="hybrid")
        except (ValueError, AttributeError) as e:
            # Fall back to vector search if hybrid is not available
            logger.warning(f"Hybrid search not available ({e}), falling back to vector search")
            if query_vector:
                return self._search_vector(query_vector, limit, file_filter, branch_filter,
                                          extensions, directories, chunk_types, languages)
            else:
                logger.error("Cannot perform hybrid search fallback: no query_vector provided")
                return []

    def _apply_filters(
        self,
        query_builder,
        file_filter: Optional[str],
        branch_filter: Optional[str],
        extensions: Optional[list[str]],
        directories: Optional[list[str]],
        chunk_types: Optional[list[str]],
        languages: Optional[list[str]]
    ):
        """Apply SQL WHERE filters to query builder."""
        # Collect all filter conditions to combine them with AND
        conditions = []

        # Extension filter: path LIKE '%.py' OR path LIKE '%.js'
        if extensions:
            ext_conditions = " OR ".join(f"path LIKE '%{ext}'" for ext in extensions)
            conditions.append(f"({ext_conditions})")

        # Directory filter: path LIKE 'src/%' OR path LIKE 'lib/%'
        if directories:
            dir_conditions = " OR ".join(f"path LIKE '{d}%'" for d in directories)
            conditions.append(f"({dir_conditions})")

        # Chunk type filter: IN clause
        if chunk_types:
            types_list = ", ".join(f"'{t}'" for t in chunk_types)
            conditions.append(f"chunk_type IN ({types_list})")

        # Language filter: IN clause
        if languages:
            lang_list = ", ".join(f"'{lang}'" for lang in languages)
            conditions.append(f"language IN ({lang_list})")

        # Keep existing filters
        if file_filter:
            conditions.append(f"path LIKE '%{file_filter}%'")

        if branch_filter:
            conditions.append(f"branch = '{branch_filter}'")

        # Combine all conditions with AND
        if conditions:
            combined_filter = " AND ".join(conditions)
            logger.debug(f"Applying combined filter: {combined_filter}")
            query_builder = query_builder.where(combined_filter)

        return query_builder

    def _convert_results(self, results: list[dict], score_type: str) -> list[SearchResult]:
        """Convert raw LanceDB results to SearchResult objects."""
        search_results = []
        for result in results:
            # Get score based on type
            if score_type == "distance":
                # For L2 distance: similarity = 1 / (1 + distance)
                distance = result.get("_distance", 0.0)
                score = 1.0 / (1.0 + distance)
            elif score_type == "fts":
                # FTS returns a score directly (higher is better)
                score = result.get("_score", 0.0)
            elif score_type == "hybrid":
                # Hybrid returns combined score
                score = result.get("_score", 0.0)
            else:
                score = 0.0

            # Remove internal fields before creating CodeChunk
            result_data = {k: v for k, v in result.items()
                          if not k.startswith("_")}
            chunk = CodeChunk(**result_data)
            search_results.append(SearchResult(chunk=chunk, score=score))

        return search_results

    def _post_filter(self, results: list[SearchResult], min_score: float) -> list[SearchResult]:
        """Filter results by minimum score threshold."""
        return [r for r in results if r.score >= min_score]

    def delete_by_path(self, path: str) -> int:
        """
        Delete all chunks for a specific file path.

        Args:
            path: File path to delete chunks for

        Returns:
            Number of chunks deleted
        """
        try:
            # Count chunks before deletion
            count_before = self.table.count_rows()

            # Delete chunks matching the path
            self.table.delete(f"path = '{path}'")

            count_after = self.table.count_rows()
            deleted = count_before - count_after

            if deleted > 0:
                logger.info(f"Deleted {deleted} chunks for {path}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete chunks for {path}: {e}")
            raise

    def delete_by_branch(self, branch: str) -> int:
        """
        Delete all chunks for a specific git branch.

        Args:
            branch: Git branch name to delete chunks for

        Returns:
            Number of chunks deleted
        """
        try:
            # Count chunks before deletion
            count_before = self.table.count_rows()

            # Delete chunks matching the branch
            self.table.delete(f"branch = '{branch}'")

            count_after = self.table.count_rows()
            deleted = count_before - count_after

            if deleted > 0:
                logger.info(f"Deleted {deleted} chunks for branch '{branch}'")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete chunks for branch {branch}: {e}")
            raise

    def get_indexed_files(self) -> set[str]:
        """
        Get set of all file paths currently indexed.

        Returns:
            Set of file paths
        """
        try:
            # Get all unique file paths from the table
            df = self.table.to_pandas()
            if df.empty:
                return set()

            unique_paths = df["path"].unique()
            return set(unique_paths)

        except Exception as e:
            logger.error(f"Failed to get indexed files: {e}")
            return set()

    def get_indexed_files_by_branch(self, branch: str) -> set[str]:
        """
        Get set of file paths indexed for a specific branch.

        Args:
            branch: Git branch name

        Returns:
            Set of file paths for the specified branch
        """
        try:
            # Query files for specific branch
            df = self.table.to_pandas()
            if df.empty:
                return set()

            # Filter by branch
            branch_df = df[df["branch"] == branch]
            unique_paths = branch_df["path"].unique()
            return set(unique_paths)

        except Exception as e:
            logger.error(f"Failed to get indexed files for branch {branch}: {e}")
            return set()

    def get_file_hash(self, path: str) -> Optional[str]:
        """
        Get the stored file hash for a given path.

        Args:
            path: File path to look up

        Returns:
            File hash if found, None otherwise
        """
        try:
            results = (
                self.table.search()
                .where(f"path = '{path}'")
                .limit(1)
                .to_list()
            )

            if results:
                return results[0].get("file_hash")

            return None

        except Exception as e:
            logger.error(f"Failed to get file hash for {path}: {e}")
            return None

    def get_stats(self) -> IndexStats:
        """
        Get statistics about the indexed content.

        Returns:
            IndexStats object with counts and metadata
        """
        try:
            total_chunks = self.table.count_rows()

            if total_chunks == 0:
                return IndexStats()

            # Get all chunks to compute stats
            all_chunks = self.table.to_pandas()

            # Count unique files
            total_files = all_chunks["path"].nunique()

            # Estimate total size (sum of text lengths)
            total_size_bytes = all_chunks["text"].str.len().sum()

            # Count by language
            languages = all_chunks["language"].value_counts().to_dict()

            # Get last indexed time
            last_indexed = all_chunks["indexed_at"].max()

            return IndexStats(
                total_files=total_files,
                total_chunks=total_chunks,
                total_size_bytes=int(total_size_bytes),
                languages=languages,
                last_indexed=float(last_indexed),
            )

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return IndexStats()

    def clear_all(self) -> None:
        """Delete all chunks from the store."""
        try:
            self.db.drop_table(self.table_name)
            self._table = None  # Reset table reference
            logger.info(f"Cleared all data from {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to clear store: {e}")
            raise

    def __repr__(self) -> str:
        """String representation."""
        return f"VectorStore(db_path={self.db_path}, table={self.table_name})"
