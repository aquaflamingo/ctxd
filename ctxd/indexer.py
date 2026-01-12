"""
Core indexing logic for ctxd.

Orchestrates file discovery, chunking, embedding generation, and storage.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Optional
import pathspec
import concurrent.futures
from threading import Lock

from .config import Config
from .embeddings import EmbeddingModel
from .store import VectorStore
from .models import CodeChunk, IndexStats
from .chunkers import TreeSitterChunker, MarkdownChunker, FallbackChunker, ChunkStrategy
from .git_utils import GitUtils
from .progress import ProgressReporter

logger = logging.getLogger(__name__)


class Indexer:
    """
    Core indexer that processes files and stores them in the vector database.

    Features:
    - File discovery with gitignore support
    - Language detection
    - Chunking strategy selection
    - Embedding generation
    - Incremental indexing (skip unchanged files)
    """

    def __init__(
        self,
        store: VectorStore,
        embeddings: EmbeddingModel,
        config: Config,
    ):
        """
        Initialize the indexer.

        Args:
            store: Vector store for persisting chunks
            embeddings: Embedding model for generating vectors
            config: Configuration object
        """
        self.store = store
        self.embeddings = embeddings
        self.config = config

        # Initialize git utilities
        self.git_utils = GitUtils()
        self.current_branch: Optional[str] = None

        # Initialize fallback chunker for unsupported languages
        self.fallback_chunker = FallbackChunker(
            max_chunk_size=config.get("indexer", "max_chunk_size", default=500),
            chunk_overlap=config.get("indexer", "chunk_overlap", default=50),
        )

        # Lazy-load language chunkers on demand (Fix 4: Performance optimization)
        # Store config for chunker creation
        self._language_chunkers: dict[str, ChunkStrategy] = {}
        self._small_file_threshold = config.get("indexer", "small_file_threshold", default=50)
        self._max_chunk_size = config.get("indexer", "max_chunk_size", default=500)

        # Parallel processing configuration
        # Use fewer workers by default to reduce overhead (4-8 is usually optimal)
        self.max_workers = config.get(
            "performance",
            "max_workers",
            default=min(8, (os.cpu_count() or 1))
        )
        self.parallel_enabled = config.get("performance", "parallel_enabled", default=True)

        # Batch embedding configuration
        self.embedding_batch_size = config.get("embeddings", "batch_size", default=64)
        self.enable_batch_embedding = config.get("performance", "batch_embedding", default=True)

        # Thread-safe locks and queues for parallel processing
        self._stats_lock = Lock()
        self._embedding_queue: list[tuple[str, dict, str, str]] = []  # (text, metadata, rel_path, file_hash)
        self._embedding_lock = Lock()
        self._in_parallel_mode = False  # Flag to enable batch embedding in parallel mode

    def _get_chunker(self, language: str) -> ChunkStrategy:
        """
        Lazy-load chunker for a specific language (Fix 4: Performance optimization).

        Args:
            language: Programming language name

        Returns:
            ChunkStrategy instance for the language
        """
        if language not in self._language_chunkers:
            logger.debug(f"Lazy-loading chunker for language: {language}")
            if language == "markdown":
                self._language_chunkers[language] = MarkdownChunker()
            elif language in ("python", "javascript", "typescript", "go"):
                self._language_chunkers[language] = TreeSitterChunker(
                    language,
                    small_file_threshold=self._small_file_threshold,
                    max_chunk_size=self._max_chunk_size
                )
            else:
                # Use fallback for unsupported languages
                return self.fallback_chunker
        return self._language_chunkers[language]

    def index_path(
        self,
        path: Path,
        force: bool = False,
        branch: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> IndexStats:
        """
        Index a file or directory.

        Args:
            path: Path to index (file or directory)
            force: Force re-indexing of unchanged files
            branch: Git branch to tag chunks with (auto-detected if None)
            progress_callback: Optional callback(ProgressEvent) for progress updates

        Returns:
            IndexStats with indexing results
        """
        path = Path(path).resolve()

        # Detect git branch (use provided or auto-detect)
        if branch is None:
            self.current_branch = self.git_utils.get_current_branch(path)
            logger.info(f"Detected git branch: {self.current_branch or 'none'}")
        else:
            self.current_branch = branch
            logger.info(f"Using specified branch: {self.current_branch}")

        if path.is_file():
            files = [path]
            # For single file, use the parent directory as base
            base_path = path.parent.resolve()
        elif path.is_dir():
            files = list(self._discover_files(path))
            # For directory, use the directory itself as base
            base_path = path.resolve()
        else:
            raise ValueError(f"Path does not exist: {path}")

        logger.info(f"Found {len(files)} files to index")

        # Initialize table before parallel processing to avoid race conditions
        # This ensures the table exists before workers start
        _ = self.store.table
        logger.debug("Database table initialized")

        # Pre-load embedding model in main thread before parallel processing
        # This ensures all workers share a single model instance
        if self.enable_batch_embedding:
            _ = self.embeddings.model
            logger.debug(f"Pre-loaded embedding model in main thread: {self.embeddings.model_name}")

        # Create progress reporter if callback provided
        reporter = None
        if progress_callback:
            reporter = ProgressReporter(len(files), callback=progress_callback)

        # Use parallel or serial processing based on configuration
        start_time = time.time()
        if self.parallel_enabled and len(files) > 1:
            indexed_files, total_chunks, skipped_files = self._index_files_parallel(
                files, base_path, force, reporter
            )
        else:
            indexed_files, total_chunks, skipped_files = self._index_files_serial(
                files, base_path, force, reporter
            )
        processing_time = time.time() - start_time

        # Flush any remaining chunks in the embedding queue
        flush_start = time.time()
        if self.enable_batch_embedding:
            flushed_chunks = self._flush_embedding_queue()
            if flushed_chunks > 0:
                flush_time = time.time() - flush_start
                logger.info(f"Flushed {flushed_chunks} remaining chunks from embedding queue ({flush_time:.2f}s)")

        # Clean up deleted files
        deleted_chunks = self._cleanup_deleted_files(base_path, files)

        total_time = time.time() - start_time
        logger.info(
            f"Indexing complete: {indexed_files} files indexed, "
            f"{skipped_files} skipped, {total_chunks} chunks added, "
            f"{deleted_chunks} chunks cleaned up "
            f"({processing_time:.2f}s processing, {total_time:.2f}s total)"
        )

        return self.store.get_stats()

    def _index_files_serial(
        self,
        files: list[Path],
        base_path: Path,
        force: bool,
        reporter: Optional[ProgressReporter]
    ) -> tuple[int, int, int]:
        """
        Index files serially (original implementation).

        Args:
            files: List of files to index
            base_path: Base path for relative path computation
            force: Force re-indexing of unchanged files
            reporter: Optional progress reporter

        Returns:
            Tuple of (indexed_files, total_chunks, skipped_files)
        """
        indexed_files = 0
        total_chunks = 0
        skipped_files = 0

        for file_path in files:
            try:
                # Update progress
                if reporter:
                    reporter.update(str(file_path))

                # Check if file should be indexed
                if not self.should_index_file(file_path):
                    skipped_files += 1
                    continue

                # Check if file changed (incremental indexing)
                if not force:
                    file_hash = self.compute_file_hash(file_path)
                    stored_hash = self.store.get_file_hash(str(file_path.relative_to(base_path)))

                    if stored_hash == file_hash:
                        logger.debug(f"Skipping unchanged file: {file_path}")
                        skipped_files += 1
                        continue

                # Index the file
                chunks_added = self._index_file(file_path, base_path=base_path)
                if chunks_added > 0:
                    indexed_files += 1
                    total_chunks += chunks_added

            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
                continue

        return indexed_files, total_chunks, skipped_files

    def _index_files_parallel(
        self,
        files: list[Path],
        base_path: Path,
        force: bool,
        reporter: Optional[ProgressReporter]
    ) -> tuple[int, int, int]:
        """
        Index files in parallel using ThreadPoolExecutor.

        Args:
            files: List of files to index
            base_path: Base path for relative path computation
            force: Force re-indexing of unchanged files
            reporter: Optional progress reporter

        Returns:
            Tuple of (indexed_files, total_chunks, skipped_files)
        """
        indexed_files = 0
        total_chunks = 0
        skipped_files = 0
        errors = 0

        logger.info(f"Using parallel indexing with {self.max_workers} workers")

        # Enable batch embedding mode for parallel processing
        self._in_parallel_mode = True

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all file processing tasks
                future_to_file = {
                    executor.submit(self._process_single_file, file_path, base_path, force): file_path
                    for file_path in files
                }

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]

                    try:
                        # Update progress
                        if reporter:
                            reporter.update(str(file_path))

                        # Get result
                        result = future.result()

                        if result["status"] == "indexed":
                            indexed_files += 1
                            total_chunks += result["chunks"]
                        elif result["status"] == "skipped":
                            skipped_files += 1
                        elif result["status"] == "error":
                            errors += 1

                    except Exception as e:
                        import traceback
                        logger.error(f"Failed to process {file_path}: {e}")
                        logger.debug(f"Traceback: {traceback.format_exc()}")
                        errors += 1

            logger.debug(f"Parallel indexing complete: {errors} errors")
            return indexed_files, total_chunks, skipped_files

        finally:
            # Disable batch embedding mode
            self._in_parallel_mode = False

    def _process_single_file(
        self,
        file_path: Path,
        base_path: Path,
        force: bool
    ) -> dict:
        """
        Process a single file for parallel indexing.

        Args:
            file_path: Path to the file
            base_path: Base path for relative path computation
            force: Force re-indexing of unchanged files

        Returns:
            Dictionary with status and metadata
        """
        try:
            # Check if file should be indexed
            if not self.should_index_file(file_path):
                return {"status": "skipped", "reason": "should_not_index"}

            # Check if file changed (incremental indexing)
            if not force:
                file_hash = self.compute_file_hash(file_path)
                stored_hash = self.store.get_file_hash(str(file_path.relative_to(base_path)))

                if stored_hash == file_hash:
                    logger.debug(f"Skipping unchanged file: {file_path}")
                    return {"status": "skipped", "reason": "unchanged"}

            # Index the file
            chunks_added = self._index_file(file_path, base_path=base_path)

            if chunks_added > 0:
                return {"status": "indexed", "chunks": chunks_added}
            else:
                return {"status": "skipped", "reason": "no_chunks"}

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {"status": "error", "error": str(e)}

    def _batch_embed_and_store(self, text: str, metadata: dict, rel_path: str, file_hash: str, language: str):
        """
        Add a chunk to the embedding queue for batch processing.

        Args:
            text: Chunk text
            metadata: Chunk metadata
            rel_path: Relative file path
            file_hash: File hash
            language: Programming language
        """
        should_flush = False
        with self._embedding_lock:
            self._embedding_queue.append((text, metadata, rel_path, file_hash, language))

            # Check if queue should be flushed
            if len(self._embedding_queue) >= self.embedding_batch_size:
                should_flush = True

        # Flush queue outside the lock to avoid deadlock
        if should_flush:
            self._flush_embedding_queue()

    def _flush_embedding_queue(self) -> int:
        """
        Process all queued chunks: generate embeddings and store.

        Returns:
            Number of chunks processed
        """
        with self._embedding_lock:
            if not self._embedding_queue:
                return 0

            # Extract data from queue
            queue_copy = self._embedding_queue[:]
            self._embedding_queue.clear()

        # Separate texts and metadata
        texts = [item[0] for item in queue_copy]
        metadatas = [item[1] for item in queue_copy]
        rel_paths = [item[2] for item in queue_copy]
        file_hashes = [item[3] for item in queue_copy]
        languages = [item[4] for item in queue_copy]

        # Generate embeddings in batch
        try:
            embed_start = time.time()
            embeddings = self.embeddings.embed_batch(texts, batch_size=self.embedding_batch_size)
            embed_time = time.time() - embed_start
            logger.debug(f"Generated {len(texts)} embeddings in {embed_time:.2f}s ({len(texts)/embed_time:.1f} chunks/s)")
        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch: {e}")
            return 0

        # Create CodeChunk objects
        chunks = []
        for i, (text, metadata, rel_path, file_hash, language, embedding) in enumerate(
            zip(texts, metadatas, rel_paths, file_hashes, languages, embeddings)
        ):
            chunk = CodeChunk(
                vector=embedding,
                text=text,
                path=rel_path,
                start_line=metadata["start_line"],
                end_line=metadata["end_line"],
                chunk_type=metadata["chunk_type"],
                name=metadata.get("name"),
                language=language,
                file_hash=file_hash,
                branch=self.current_branch,
            )
            chunks.append(chunk)

        # Store chunks
        try:
            self.store.add_chunks(chunks)
            logger.debug(f"Flushed and stored {len(chunks)} chunks from embedding queue")
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            return 0

        return len(chunks)

    def _discover_files(self, root_path: Path) -> list[Path]:
        """
        Discover indexable files in a directory tree.

        Respects .gitignore patterns and configuration exclusions.

        Args:
            root_path: Root directory to search

        Returns:
            List of file paths to index
        """
        # Load nested gitignore patterns
        gitignore_spec = self._load_gitignores(root_path)

        # Get exclude patterns from config
        exclude_patterns = self.config.get("indexer", "exclude", default=[])

        files = []
        for file_path in root_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Get path relative to root for pattern matching
            rel_path = file_path.relative_to(root_path)

            # Check gitignore
            if gitignore_spec and gitignore_spec.match_file(str(rel_path)):
                continue

            # Check exclude patterns
            if self._matches_any_pattern(str(rel_path), exclude_patterns):
                continue

            files.append(file_path)

        return files

    def _load_gitignores(self, root_path: Path) -> Optional[pathspec.PathSpec]:
        """
        Load and merge all nested .gitignore files from directory tree.

        Args:
            root_path: Root directory to search for .gitignore files

        Returns:
            PathSpec object with merged patterns or None
        """
        return self.git_utils.load_nested_gitignore(root_path)

    def _matches_any_pattern(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any of the given glob patterns."""
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        return spec.match_file(path)

    def should_index_file(self, file_path: Path) -> bool:
        """
        Check if a file should be indexed.

        Args:
            file_path: Path to check

        Returns:
            True if file should be indexed
        """
        # Check file size (default 2MB, increased from 1MB for Phase 6)
        max_size = self.config.get("indexer", "max_file_size", default=2097152)
        try:
            file_size = file_path.stat().st_size
            if file_size > max_size:
                logger.warning(
                    f"Skipping large file: {file_path} "
                    f"({file_size / 1024 / 1024:.1f}MB > {max_size / 1024 / 1024:.1f}MB limit)"
                )
                return False
        except OSError as e:
            logger.debug(f"Cannot stat file {file_path}: {e}")
            return False

        # Check if it's a text file (basic heuristic)
        try:
            # Use errors='ignore' to handle encoding issues gracefully
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                f.read(1024)  # Try to read first 1KB
            return True
        except OSError as e:
            logger.debug(f"Cannot read file {file_path}: {e}")
            return False

    def _cleanup_deleted_files(
        self,
        indexed_path: Path,
        current_files: list[Path]
    ) -> int:
        """
        Remove chunks for files that no longer exist.

        Args:
            indexed_path: Base path that was indexed
            current_files: List of files currently discovered

        Returns:
            Number of chunks deleted
        """
        # Check if cleanup is enabled in config
        cleanup_enabled = self.config.get("git", "cleanup_deleted", default=True)
        if not cleanup_enabled:
            logger.debug("Deleted file cleanup is disabled")
            return 0

        try:
            # Get set of currently indexed files
            if self.current_branch:
                indexed_files = self.store.get_indexed_files_by_branch(self.current_branch)
            else:
                indexed_files = self.store.get_indexed_files()

            # Convert current_files to relative paths
            current_file_set = {str(f.relative_to(indexed_path)) for f in current_files}

            # Find deleted files
            deleted_files = indexed_files - current_file_set

            if not deleted_files:
                logger.debug("No deleted files to clean up")
                return 0

            # Delete chunks for each deleted file
            total_deleted = 0
            for deleted_file in deleted_files:
                count = self.store.delete_by_path(deleted_file)
                total_deleted += count
                if count > 0:
                    logger.info(f"Cleaned up {count} chunks for deleted file: {deleted_file}")

            return total_deleted

        except Exception as e:
            logger.error(f"Failed to cleanup deleted files: {e}")
            return 0

    def _index_file(self, file_path: Path, base_path: Path) -> int:
        """
        Index a single file.

        Args:
            file_path: Path to the file
            base_path: Base path for computing relative paths

        Returns:
            Number of chunks added
        """
        # Read file content with graceful encoding error handling
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return 0

        # Skip empty files
        if not content.strip():
            logger.debug(f"Skipping empty file: {file_path}")
            return 0

        # Compute file hash
        file_hash = self.compute_file_hash(file_path)

        # Get relative path
        rel_path = str(file_path.relative_to(base_path))

        # Delete old chunks for this file
        self.store.delete_by_path(rel_path)

        # Detect language and select chunker (lazy-loaded)
        language = self.detect_language(file_path)
        chunker = self._get_chunker(language)

        # Chunk the content
        chunks_data = chunker.chunk(content, str(file_path))

        if not chunks_data:
            logger.debug(f"No chunks extracted from {file_path}")
            return 0

        # Use batch embedding only when processing multiple files in parallel
        # For single file or serial processing, embed immediately for backward compatibility
        if self.enable_batch_embedding and hasattr(self, '_in_parallel_mode') and self._in_parallel_mode:
            # Queue chunks for batch processing
            for text, metadata in chunks_data:
                self._batch_embed_and_store(text, metadata, rel_path, file_hash, language)

            logger.debug(f"Queued {len(chunks_data)} chunks from {file_path} for batch embedding")
            return len(chunks_data)
        else:
            # Original immediate embedding approach
            chunk_texts = [text for text, _ in chunks_data]
            embeddings = self.embeddings.embed_batch(chunk_texts)

            # Create CodeChunk objects
            chunks = []
            for (text, metadata), embedding in zip(chunks_data, embeddings):
                chunk = CodeChunk(
                    vector=embedding,
                    text=text,
                    path=rel_path,
                    start_line=metadata["start_line"],
                    end_line=metadata["end_line"],
                    chunk_type=metadata["chunk_type"],
                    name=metadata.get("name"),
                    language=language,
                    file_hash=file_hash,
                    branch=self.current_branch,
                )
                chunks.append(chunk)

            # Store chunks
            self.store.add_chunks(chunks)

            logger.debug(f"Indexed {file_path}: {len(chunks)} chunks")
            return len(chunks)

    def detect_language(self, file_path: Path) -> str:
        """
        Detect the programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name (lowercase)
        """
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
        }

        ext = file_path.suffix.lower()
        return extension_map.get(ext, "unknown")

    def compute_file_hash(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of file content.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest of the hash
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute hash for {file_path}: {e}")
            return ""

    def __repr__(self) -> str:
        """String representation."""
        return f"Indexer(store={self.store})"
