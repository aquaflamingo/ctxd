"""
Unit tests for the vector store.

Tests LanceDB abstraction for storing and searching code chunks.
"""

import pytest
from ctxd.models import CodeChunk
from ctxd.store import VectorStore


def test_store_initialization(vector_store):
    """Test that store initializes correctly."""
    assert vector_store is not None
    assert vector_store.db_path.parent.exists()


def test_add_and_search_chunks(vector_store):
    """Test adding chunks and retrieving them via search."""
    # Create sample chunks
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="def hello(): print('hello')",
            path="test.py",
            start_line=1,
            end_line=1,
            chunk_type="function",
            name="hello",
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.2] * 384,
            text="def goodbye(): print('goodbye')",
            path="test.py",
            start_line=3,
            end_line=3,
            chunk_type="function",
            name="goodbye",
            language="python",
            file_hash="hash1",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Search with a similar vector
    query_vector = [0.15] * 384
    results = vector_store.search(query_vector, limit=5)

    assert len(results) > 0
    assert all(r.chunk.path == "test.py" for r in results)
    assert all(0.0 <= r.score <= 1.0 for r in results)


def test_delete_by_path(vector_store):
    """Test deleting chunks by file path."""
    # Add chunks from two different files
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="file1 content",
            path="file1.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.2] * 384,
            text="file2 content",
            path="file2.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash2",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Delete chunks from file1.py
    deleted = vector_store.delete_by_path("file1.py")
    assert deleted > 0

    # Search should only return file2.py chunks
    query_vector = [0.15] * 384
    results = vector_store.search(query_vector, limit=10)

    file_paths = [r.chunk.path for r in results]
    assert "file1.py" not in file_paths
    assert "file2.py" in file_paths


def test_get_file_hash(vector_store):
    """Test retrieving stored file hash."""
    chunk = CodeChunk(
        vector=[0.1] * 384,
        text="content",
        path="test.py",
        start_line=1,
        end_line=1,
        chunk_type="block",
        name=None,
        language="python",
        file_hash="abc123",
    )

    vector_store.add_chunks([chunk])

    stored_hash = vector_store.get_file_hash("test.py")
    assert stored_hash == "abc123"


def test_get_file_hash_nonexistent(vector_store):
    """Test getting hash for nonexistent file returns None."""
    stored_hash = vector_store.get_file_hash("nonexistent.py")
    assert stored_hash is None


def test_get_stats_empty(vector_store):
    """Test stats on empty database."""
    stats = vector_store.get_stats()

    assert stats.total_files == 0
    assert stats.total_chunks == 0
    assert stats.total_size_bytes == 0


def test_get_stats_with_data(vector_store):
    """Test stats with indexed data."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="content1",
            path="file1.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.2] * 384,
            text="content2",
            path="file1.py",
            start_line=2,
            end_line=2,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.3] * 384,
            text="content3",
            path="file2.js",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="javascript",
            file_hash="hash2",
        ),
    ]

    vector_store.add_chunks(chunks)
    stats = vector_store.get_stats()

    assert stats.total_files == 2
    assert stats.total_chunks == 3
    assert stats.total_size_bytes > 0
    assert "python" in stats.languages
    assert "javascript" in stats.languages


def test_search_with_file_filter(vector_store):
    """Test searching with file pattern filter."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="python content",
            path="code.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.1] * 384,  # Same vector for testing filter
            text="js content",
            path="code.js",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="javascript",
            file_hash="hash2",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Search with filter for .py files
    query_vector = [0.1] * 384
    results = vector_store.search(query_vector, limit=10, file_filter=".py")

    # Should only get .py results
    assert all(".py" in r.chunk.path for r in results)


def test_search_with_min_score(vector_store):
    """Test search with minimum score threshold."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="content",
            path="test.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Search with very high min_score (should filter out results)
    query_vector = [0.5] * 384  # Very different vector
    results = vector_store.search(query_vector, limit=10, min_score=0.99)

    # Should get few or no results due to high threshold
    assert len(results) < len(chunks)


def test_clear_all(vector_store):
    """Test clearing all data from store."""
    chunk = CodeChunk(
        vector=[0.1] * 384,
        text="content",
        path="test.py",
        start_line=1,
        end_line=1,
        chunk_type="block",
        name=None,
        language="python",
        file_hash="hash1",
    )

    vector_store.add_chunks([chunk])

    # Verify data exists
    stats = vector_store.get_stats()
    assert stats.total_chunks > 0

    # Clear all
    vector_store.clear_all()

    # Verify data is gone
    stats = vector_store.get_stats()
    assert stats.total_chunks == 0


def test_store_repr(vector_store):
    """Test string representation."""
    repr_str = repr(vector_store)
    assert "VectorStore" in repr_str
    assert str(vector_store.db_path) in repr_str


# ============================================================================
# Phase 3 Tests - Branch Operations
# ============================================================================


def test_delete_by_branch(vector_store):
    """Delete chunks for specific branch (Phase 3)."""
    # Add chunks with different branches
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="main content",
            path="file.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
            branch="main",
        ),
        CodeChunk(
            vector=[0.2] * 384,
            text="feature content",
            path="file.py",
            start_line=2,
            end_line=2,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
            branch="feature",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Delete feature branch chunks
    deleted = vector_store.delete_by_branch("feature")
    assert deleted > 0

    # Verify only main branch chunks remain
    stats = vector_store.get_stats()
    assert stats.total_chunks == 1


def test_get_indexed_files(vector_store):
    """Retrieve set of indexed file paths (Phase 3)."""
    # Add chunks for multiple files
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="content1",
            path="file1.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.2] * 384,
            text="content2",
            path="file1.py",
            start_line=2,
            end_line=2,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.3] * 384,
            text="content3",
            path="file2.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash2",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Get indexed files
    files = vector_store.get_indexed_files()

    # Should contain both files
    assert "file1.py" in files
    assert "file2.py" in files
    assert len(files) == 2


def test_get_indexed_files_empty(vector_store):
    """Return empty set when no files indexed (Phase 3)."""
    files = vector_store.get_indexed_files()
    assert len(files) == 0


def test_get_indexed_files_by_branch(vector_store):
    """Get files indexed for specific branch (Phase 3)."""
    # Add chunks for different branches
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="main content",
            path="file1.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
            branch="main",
        ),
        CodeChunk(
            vector=[0.2] * 384,
            text="feature content",
            path="file2.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash2",
            branch="feature",
        ),
        CodeChunk(
            vector=[0.3] * 384,
            text="main content 2",
            path="file3.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash3",
            branch="main",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Get files for main branch
    main_files = vector_store.get_indexed_files_by_branch("main")
    assert "file1.py" in main_files
    assert "file3.py" in main_files
    assert "file2.py" not in main_files

    # Get files for feature branch
    feature_files = vector_store.get_indexed_files_by_branch("feature")
    assert "file2.py" in feature_files
    assert len(feature_files) == 1


def test_branch_filtered_search(vector_store):
    """Search can filter by branch (Phase 3)."""
    # Add chunks for main and feature branches
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="main branch code",
            path="file.py",
            start_line=1,
            end_line=1,
            chunk_type="function",
            name="main_func",
            language="python",
            file_hash="hash1",
            branch="main",
        ),
        CodeChunk(
            vector=[0.1] * 384,  # Same vector for testing filter
            text="feature branch code",
            path="file.py",
            start_line=10,
            end_line=10,
            chunk_type="function",
            name="feature_func",
            language="python",
            file_hash="hash1",
            branch="feature",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Search with branch filter for main
    query_vector = [0.1] * 384
    results = vector_store.search(
        query_vector,
        limit=10,
        branch_filter="main"
    )

    # Should only get main branch results
    assert all(r.chunk.branch == "main" for r in results)
    assert len(results) == 1

    # Search with branch filter for feature
    results = vector_store.search(
        query_vector,
        limit=10,
        branch_filter="feature"
    )

    # Should only get feature branch results
    assert all(r.chunk.branch == "feature" for r in results)
    assert len(results) == 1


def test_search_without_branch_filter_returns_all(vector_store):
    """Search without branch filter returns all branches (Phase 3)."""
    # Add chunks for different branches
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="content",
            path="file.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
            branch="main",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="content",
            path="file.py",
            start_line=2,
            end_line=2,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
            branch="feature",
        ),
    ]

    vector_store.add_chunks(chunks)

    # Search without branch filter
    query_vector = [0.1] * 384
    results = vector_store.search(query_vector, limit=10)

    # Should get results from both branches
    branches = {r.chunk.branch for r in results}
    assert "main" in branches
    assert "feature" in branches
    assert len(results) == 2


# ============================================================================
# Phase 4 Tests - Hybrid Search and Rich Filtering
# ============================================================================


def test_search_vector_mode(vector_store):
    """Test pure vector search mode (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="test function for authentication",
            path="auth.py",
            start_line=1,
            end_line=5,
            chunk_type="function",
            name="authenticate",
            language="python",
            file_hash="hash1",
        ),
    ]
    vector_store.add_chunks(chunks)

    query_vector = [0.1] * 384
    results = vector_store.search(
        query_vector=query_vector,
        limit=10,
        mode="vector"
    )

    assert len(results) > 0
    assert all(r.score > 0 for r in results)


def test_search_fts_mode(vector_store):
    """Test FTS (keyword) search mode (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="def authenticate_user(username, password):",
            path="auth.py",
            start_line=1,
            end_line=5,
            chunk_type="function",
            name="authenticate_user",
            language="python",
            file_hash="hash1",
        ),
    ]
    vector_store.add_chunks(chunks)

    # FTS search for exact keyword
    results = vector_store.search(
        query_text="authenticate",
        limit=10,
        mode="fts"
    )

    assert len(results) > 0
    assert any("authenticate" in r.chunk.text.lower() for r in results)


def test_search_hybrid_mode(vector_store):
    """Test hybrid search combining vector and FTS (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="def authenticate_user(username, password):",
            path="auth.py",
            start_line=1,
            end_line=5,
            chunk_type="function",
            name="authenticate_user",
            language="python",
            file_hash="hash1",
        ),
    ]
    vector_store.add_chunks(chunks)

    # Hybrid search combines semantic and keyword
    results = vector_store.search(
        query_text="authenticate",
        query_vector=[0.15] * 384,
        limit=10,
        mode="hybrid"
    )

    assert len(results) > 0


def test_search_with_extension_filter(vector_store):
    """Test filtering by file extensions (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="python code",
            path="file.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="javascript code",
            path="file.js",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="javascript",
            file_hash="hash2",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="typescript code",
            path="file.ts",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="typescript",
            file_hash="hash3",
        ),
    ]
    vector_store.add_chunks(chunks)

    # Filter for Python files only
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        extensions=[".py"],
        mode="vector"
    )

    assert all(r.chunk.path.endswith(".py") for r in results)

    # Filter for JS and TS files
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        extensions=[".js", ".ts"],
        mode="vector"
    )

    assert all(r.chunk.path.endswith((".js", ".ts")) for r in results)


def test_search_with_directory_filter(vector_store):
    """Test filtering by directory paths (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="src code",
            path="src/main.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="lib code",
            path="lib/utils.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash2",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="test code",
            path="tests/test_main.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash3",
        ),
    ]
    vector_store.add_chunks(chunks)

    # Filter for src directory
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        directories=["src/"],
        mode="vector"
    )

    assert all(r.chunk.path.startswith("src/") for r in results)


def test_search_with_chunk_type_filter(vector_store):
    """Test filtering by chunk type (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="def my_function():",
            path="file.py",
            start_line=1,
            end_line=3,
            chunk_type="function",
            name="my_function",
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="class MyClass:",
            path="file.py",
            start_line=5,
            end_line=10,
            chunk_type="class",
            name="MyClass",
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="# some comment",
            path="file.py",
            start_line=12,
            end_line=12,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
    ]
    vector_store.add_chunks(chunks)

    # Filter for functions only
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        chunk_types=["function"],
        mode="vector"
    )

    assert all(r.chunk.chunk_type == "function" for r in results)

    # Filter for functions and classes
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        chunk_types=["function", "class"],
        mode="vector"
    )

    assert all(r.chunk.chunk_type in ["function", "class"] for r in results)


def test_search_with_language_filter(vector_store):
    """Test filtering by programming language (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="python code",
            path="file.py",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="python",
            file_hash="hash1",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="javascript code",
            path="file.js",
            start_line=1,
            end_line=1,
            chunk_type="block",
            name=None,
            language="javascript",
            file_hash="hash2",
        ),
    ]
    vector_store.add_chunks(chunks)

    # Filter for Python only
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        languages=["python"],
        mode="vector"
    )

    assert all(r.chunk.language == "python" for r in results)


def test_search_with_multiple_filters(vector_store):
    """Test combining multiple filters (Phase 4)."""
    chunks = [
        CodeChunk(
            vector=[0.1] * 384,
            text="def py_func():",
            path="src/main.py",
            start_line=1,
            end_line=3,
            chunk_type="function",
            name="py_func",
            language="python",
            file_hash="hash1",
            branch="main",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="function jsFunc()",
            path="src/main.js",
            start_line=1,
            end_line=3,
            chunk_type="function",
            name="jsFunc",
            language="javascript",
            file_hash="hash2",
            branch="main",
        ),
        CodeChunk(
            vector=[0.1] * 384,
            text="class PyClass:",
            path="lib/utils.py",
            start_line=1,
            end_line=5,
            chunk_type="class",
            name="PyClass",
            language="python",
            file_hash="hash3",
            branch="main",
        ),
    ]
    vector_store.add_chunks(chunks)

    # Combine: src directory + Python + functions
    results = vector_store.search(
        query_vector=[0.1] * 384,
        limit=10,
        directories=["src/"],
        languages=["python"],
        chunk_types=["function"],
        mode="vector"
    )

    # Should only get Python functions from src/
    assert len(results) == 1
    assert results[0].chunk.name == "py_func"
