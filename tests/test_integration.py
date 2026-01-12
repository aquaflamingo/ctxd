"""
Integration tests for ctxd.

Tests the full workflow from indexing to searching.
"""

import pytest
from pathlib import Path
from ctxd import Config, EmbeddingModel, VectorStore, Indexer


def test_full_index_and_search_workflow(sample_codebase):
    """Test the complete workflow: index → search → get results."""
    # Setup
    config = Config(project_root=sample_codebase)
    db_path = sample_codebase / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel()
    indexer = Indexer(store, embeddings, config)

    # Index the codebase
    stats = indexer.index_path(sample_codebase, force=False)

    assert stats.total_files > 0
    assert stats.total_chunks > 0
    assert stats.total_size_bytes > 0

    # Perform a search
    query = "utility function"
    query_vector = embeddings.embed_text(query)
    results = store.search(query_vector, limit=10)

    assert len(results) > 0

    # Verify search results have expected fields
    for result in results:
        assert result.chunk.path is not None
        assert result.chunk.text is not None
        assert result.chunk.start_line > 0
        assert result.chunk.end_line >= result.chunk.start_line
        assert 0.0 <= result.score <= 1.0


def test_incremental_reindex(sample_codebase):
    """Test incremental re-indexing after file changes."""
    # Setup
    config = Config(project_root=sample_codebase)
    db_path = sample_codebase / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel()
    indexer = Indexer(store, embeddings, config)

    # Initial index
    stats1 = indexer.index_path(sample_codebase, force=False)
    initial_chunks = stats1.total_chunks

    # Modify a file
    utils_file = sample_codebase / "src" / "utils.py"
    original_content = utils_file.read_text()
    utils_file.write_text(original_content + "\n\ndef new_utility():\n    return 'new'\n")

    # Re-index
    stats2 = indexer.index_path(sample_codebase, force=False)

    # Should have more chunks now due to new function
    assert stats2.total_chunks >= initial_chunks

    # Search for the new function
    query = "new utility"
    query_vector = embeddings.embed_text(query)
    results = store.search(query_vector, limit=5)

    # Should find the new function
    assert any("new_utility" in r.chunk.text for r in results)


def test_search_relevance(sample_codebase):
    """Test that search returns relevant results."""
    # Setup
    config = Config(project_root=sample_codebase)
    db_path = sample_codebase / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel()
    indexer = Indexer(store, embeddings, config)

    # Index
    indexer.index_path(sample_codebase, force=False)

    # Search for main function
    query = "main entry point function"
    query_vector = embeddings.embed_text(query)
    results = store.search(query_vector, limit=5)

    assert len(results) > 0

    # Top result should contain "main"
    top_result = results[0]
    assert "main" in top_result.chunk.text.lower() or "main" in (top_result.chunk.name or "").lower()


def test_multiple_languages_indexed(sample_codebase):
    """Test that multiple languages are correctly indexed."""
    # Setup
    config = Config(project_root=sample_codebase)
    db_path = sample_codebase / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel()
    indexer = Indexer(store, embeddings, config)

    # Add a JavaScript file
    (sample_codebase / "app.js").write_text('''
function greet(name) {
    console.log("Hello, " + name);
}
''')

    # Index
    indexer.index_path(sample_codebase, force=False)

    # Get stats
    stats = store.get_stats()

    # Should have both Python and JavaScript
    assert "python" in stats.languages
    assert "javascript" in stats.languages


def test_gitignore_respected_in_workflow(temp_dir):
    """Test that .gitignore patterns are respected in full workflow."""
    # Create .gitignore
    (temp_dir / ".gitignore").write_text("*.pyc\n__pycache__/\n")

    # Create files
    (temp_dir / "main.py").write_text("print('hello')")
    (temp_dir / "__pycache__").mkdir()
    (temp_dir / "__pycache__" / "cache.pyc").write_text("bytecode")

    # Setup and index
    config = Config(project_root=temp_dir)
    db_path = temp_dir / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel()
    indexer = Indexer(store, embeddings, config)

    stats = indexer.index_path(temp_dir, force=False)

    # Should have indexed main.py but not __pycache__
    query = "hello"
    query_vector = embeddings.embed_text(query)
    results = store.search(query_vector, limit=10)

    file_paths = [r.chunk.path for r in results]
    assert any("main.py" in p for p in file_paths)
    assert not any("__pycache__" in p for p in file_paths)
    assert not any(".pyc" in p for p in file_paths)


def test_stats_accuracy(sample_codebase):
    """Test that index statistics are accurate."""
    # Setup
    config = Config(project_root=sample_codebase)
    db_path = sample_codebase / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel()
    indexer = Indexer(store, embeddings, config)

    # Index
    indexer.index_path(sample_codebase, force=False)

    # Get stats
    stats = store.get_stats()

    # Verify stats make sense
    assert stats.total_files > 0
    assert stats.total_chunks >= stats.total_files  # At least one chunk per file
    assert stats.total_size_bytes > 0
    assert len(stats.languages) > 0
    assert stats.last_indexed is not None
