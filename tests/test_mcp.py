"""
Unit tests for the MCP server.

Tests MCP server tools (ctx_search, ctx_status, ctx_index) and integration
with ctxd components.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ctxd.mcp_server import (
    initialize,
    ctx_search,
    ctx_status,
    ctx_index,
    store,
    embeddings,
    indexer,
    config,
)
from ctxd.models import CodeChunk, SearchResult


@pytest.fixture
def initialized_mcp(sample_codebase, vector_store, embedding_model, config):
    """Initialize MCP server with test components."""
    # Monkey-patch the global instances
    import ctxd.mcp_server as mcp_module
    mcp_module.store = vector_store
    mcp_module.embeddings = embedding_model
    mcp_module.indexer = pytest.fixture
    mcp_module.config = config

    # Create indexer
    from ctxd.indexer import Indexer
    test_indexer = Indexer(vector_store, embedding_model, config)
    mcp_module.indexer = test_indexer

    # Index the sample codebase
    test_indexer.index_path(sample_codebase, force=True)

    yield {
        "store": vector_store,
        "embeddings": embedding_model,
        "indexer": test_indexer,
        "config": config,
        "codebase": sample_codebase,
    }

    # Cleanup
    mcp_module.store = None
    mcp_module.embeddings = None
    mcp_module.indexer = None
    mcp_module.config = None


def test_ctx_search_returns_results(initialized_mcp):
    """Test that ctx_search returns relevant results."""
    result = ctx_search(query="utility function", limit=5)

    assert "error" not in result or result["error"] is None
    assert "results" in result
    assert isinstance(result["results"], list)
    assert result["count"] >= 0

    # If there are results, verify structure
    if result["count"] > 0:
        first_result = result["results"][0]
        assert "path" in first_result
        assert "start_line" in first_result
        assert "end_line" in first_result
        assert "code" in first_result
        assert "score" in first_result
        assert "language" in first_result
        assert "chunk_type" in first_result
        assert 0.0 <= first_result["score"] <= 1.0


def test_ctx_search_with_file_filter(initialized_mcp):
    """Test ctx_search with file filter."""
    result = ctx_search(query="function", limit=10, file_filter="utils.py")

    assert "results" in result
    # All results should match the filter
    for item in result["results"]:
        assert "utils.py" in item["path"]


def test_ctx_search_respects_limit(initialized_mcp):
    """Test that ctx_search respects the limit parameter."""
    result = ctx_search(query="function", limit=2)

    assert result["count"] <= 2
    assert len(result["results"]) <= 2


def test_ctx_search_without_initialization():
    """Test ctx_search behavior when components aren't initialized."""
    import ctxd.mcp_server as mcp_module

    # Save original values
    original_store = mcp_module.store
    original_embeddings = mcp_module.embeddings

    # Set to None to simulate uninitialized state
    mcp_module.store = None
    mcp_module.embeddings = None

    result = ctx_search(query="test")

    assert "error" in result
    assert "not initialized" in result["error"].lower()
    assert result["results"] == []

    # Restore original values
    mcp_module.store = original_store
    mcp_module.embeddings = original_embeddings


def test_ctx_status_returns_stats(initialized_mcp):
    """Test that ctx_status returns index statistics."""
    result = ctx_status()

    assert "error" not in result or result["error"] is None
    assert "total_files" in result
    assert "total_chunks" in result
    assert "total_size_mb" in result
    assert "languages" in result
    assert "indexed" in result

    # Should have indexed content
    assert result["total_files"] > 0
    assert result["total_chunks"] > 0
    assert result["indexed"] is True
    assert isinstance(result["languages"], dict)


def test_ctx_status_without_initialization():
    """Test ctx_status behavior when store isn't initialized."""
    import ctxd.mcp_server as mcp_module

    # Save original value
    original_store = mcp_module.store

    # Set to None to simulate uninitialized state
    mcp_module.store = None

    result = ctx_status()

    assert "error" in result
    assert "not initialized" in result["error"].lower()

    # Restore original value
    mcp_module.store = original_store


def test_ctx_index_indexes_directory(initialized_mcp):
    """Test that ctx_index successfully indexes a directory."""
    codebase = initialized_mcp["codebase"]

    # Create a new file in the codebase
    new_file = codebase / "new_module.py"
    new_file.write_text('''
def new_function():
    """A newly added function."""
    return "new"
''')

    result = ctx_index(path=".", force=True)

    assert "error" not in result or result["error"] is None
    assert "total_files" in result
    assert "total_chunks" in result
    assert result["total_files"] > 0
    assert result["total_chunks"] > 0

    # Should include the new file
    stats_result = ctx_status()
    assert stats_result["total_files"] > 0


def test_ctx_index_with_nonexistent_path(initialized_mcp):
    """Test ctx_index with a path that doesn't exist."""
    result = ctx_index(path="nonexistent/directory")

    assert "error" in result
    assert "does not exist" in result["error"].lower()


def test_ctx_index_with_force_flag(initialized_mcp):
    """Test ctx_index with force=True re-indexes everything."""
    # Index once
    result1 = ctx_index(path=".", force=False)

    # Index again with force
    result2 = ctx_index(path=".", force=True)

    # Both should succeed
    assert "error" not in result1 or result1["error"] is None
    assert "error" not in result2 or result2["error"] is None

    # Should have indexed content
    assert result2["total_chunks"] > 0


def test_ctx_index_without_initialization():
    """Test ctx_index behavior when components aren't initialized."""
    import ctxd.mcp_server as mcp_module

    # Save original values
    original_indexer = mcp_module.indexer
    original_config = mcp_module.config

    # Set to None to simulate uninitialized state
    mcp_module.indexer = None
    mcp_module.config = None

    result = ctx_index(path=".")

    assert "error" in result
    assert "not initialized" in result["error"].lower()

    # Restore original values
    mcp_module.indexer = original_indexer
    mcp_module.config = original_config


def test_initialize_function(temp_dir, sample_python_file):
    """Test the initialize function."""
    # Create .ctxd directory
    ctxd_dir = temp_dir / ".ctxd"
    ctxd_dir.mkdir()

    # Create a minimal config file
    config_file = ctxd_dir / "config.toml"
    config_file.write_text("[indexer]\n")

    initialize(temp_dir)

    import ctxd.mcp_server as mcp_module

    # Verify components are initialized
    assert mcp_module.store is not None
    assert mcp_module.embeddings is not None
    assert mcp_module.indexer is not None
    assert mcp_module.config is not None

    # Cleanup
    mcp_module.store = None
    mcp_module.embeddings = None
    mcp_module.indexer = None
    mcp_module.config = None


def test_mcp_search_handles_malformed_requests(initialized_mcp):
    """Test that ctx_search handles edge cases gracefully."""
    # Empty query
    result = ctx_search(query="", limit=5)
    assert "results" in result

    # Very large limit
    result = ctx_search(query="test", limit=1000)
    assert "results" in result
    assert len(result["results"]) <= 1000

    # Zero limit
    result = ctx_search(query="test", limit=0)
    assert "results" in result
    assert len(result["results"]) == 0


def test_ctx_search_query_response_structure(initialized_mcp):
    """Test that search response has the expected structure."""
    result = ctx_search(query="function")

    # Top-level structure
    assert isinstance(result, dict)
    assert "query" in result
    assert result["query"] == "function"
    assert "count" in result
    assert "results" in result
    assert isinstance(result["results"], list)

    # Result item structure
    if result["count"] > 0:
        item = result["results"][0]
        required_fields = [
            "path", "start_line", "end_line", "code",
            "score", "language", "chunk_type", "name"
        ]
        for field in required_fields:
            assert field in item


def test_ctx_status_with_empty_index(vector_store):
    """Test ctx_status when index is empty."""
    import ctxd.mcp_server as mcp_module

    # Save original value
    original_store = mcp_module.store

    # Set to empty store
    mcp_module.store = vector_store

    result = ctx_status()

    assert result["total_files"] == 0
    assert result["total_chunks"] == 0
    assert result["indexed"] is False

    # Restore original value
    mcp_module.store = original_store
