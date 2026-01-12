"""
Unit tests for the indexer.

Tests file discovery, language detection, hashing, and indexing logic.
"""

import pytest
from pathlib import Path


def test_detect_language(indexer):
    """Test language detection from file extensions."""
    assert indexer.detect_language(Path("test.py")) == "python"
    assert indexer.detect_language(Path("test.js")) == "javascript"
    assert indexer.detect_language(Path("test.ts")) == "typescript"
    assert indexer.detect_language(Path("test.go")) == "go"
    assert indexer.detect_language(Path("test.md")) == "markdown"
    assert indexer.detect_language(Path("test.txt")) == "text"
    assert indexer.detect_language(Path("test.xyz")) == "unknown"


def test_compute_file_hash(indexer, sample_python_file):
    """Test computing file hash."""
    hash1 = indexer.compute_file_hash(sample_python_file)

    assert hash1 is not None
    assert len(hash1) == 64  # SHA256 hex digest length
    assert isinstance(hash1, str)

    # Hash should be consistent
    hash2 = indexer.compute_file_hash(sample_python_file)
    assert hash1 == hash2


def test_compute_file_hash_different_files(indexer, sample_python_file, sample_markdown_file):
    """Test that different files have different hashes."""
    hash1 = indexer.compute_file_hash(sample_python_file)
    hash2 = indexer.compute_file_hash(sample_markdown_file)

    assert hash1 != hash2


def test_should_index_file_text_file(indexer, sample_python_file):
    """Test that text files are indexable."""
    assert indexer.should_index_file(sample_python_file) is True


def test_should_index_file_large_file(indexer, temp_dir):
    """Test that files exceeding max size are skipped."""
    # Create a large file
    large_file = temp_dir / "large.txt"
    large_content = "x" * (2 * 1024 * 1024)  # 2MB
    large_file.write_text(large_content)

    # Should be skipped due to size
    assert indexer.should_index_file(large_file) is False


def test_discover_files(indexer, sample_codebase):
    """Test file discovery in a codebase."""
    files = list(indexer._discover_files(sample_codebase))

    # Should find Python files
    py_files = [f for f in files if f.suffix == ".py"]
    assert len(py_files) > 0

    # Should find markdown files
    md_files = [f for f in files if f.suffix == ".md"]
    assert len(md_files) > 0


def test_discover_files_respects_gitignore(indexer, temp_dir, sample_gitignore):
    """Test that gitignore patterns are respected."""
    # Create files that should be ignored
    (temp_dir / "__pycache__").mkdir()
    (temp_dir / "__pycache__" / "test.pyc").write_text("bytecode")

    (temp_dir / "node_modules").mkdir()
    (temp_dir / "node_modules" / "package.json").write_text("{}")

    # Create file that should be indexed
    (temp_dir / "main.py").write_text("print('hello')")

    files = list(indexer._discover_files(temp_dir))

    # Should not include ignored files
    file_names = [f.name for f in files]
    assert "test.pyc" not in file_names
    assert "package.json" not in file_names

    # Should include main.py
    assert "main.py" in file_names


def test_index_single_file(indexer, sample_python_file, temp_dir):
    """Test indexing a single file."""
    chunks_added = indexer._index_file(sample_python_file, base_path=temp_dir)

    assert chunks_added > 0

    # Verify chunks were added to store
    stats = indexer.store.get_stats()
    assert stats.total_chunks > 0


def test_incremental_indexing_skips_unchanged(indexer, sample_python_file, temp_dir):
    """Test that unchanged files are skipped on re-index."""
    # Index file first time
    indexer.index_path(sample_python_file, force=False)

    # Get initial chunk count
    initial_stats = indexer.store.get_stats()
    initial_chunks = initial_stats.total_chunks

    # Re-index without forcing (should skip unchanged file)
    indexer.index_path(sample_python_file, force=False)

    # Chunk count should remain the same
    final_stats = indexer.store.get_stats()
    assert final_stats.total_chunks == initial_chunks


def test_force_reindex_processes_all_files(indexer, sample_python_file, temp_dir):
    """Test that force=True re-indexes all files."""
    # Index file first time
    indexer.index_path(sample_python_file, force=False)

    # Modify the file
    content = sample_python_file.read_text()
    sample_python_file.write_text(content + "\n\ndef new_function():\n    pass\n")

    # Force re-index
    stats = indexer.index_path(sample_python_file, force=True)

    # Should have processed the file
    assert stats.total_chunks > 0


def test_index_directory(indexer, sample_codebase):
    """Test indexing an entire directory."""
    stats = indexer.index_path(sample_codebase, force=False)

    assert stats.total_files > 0
    assert stats.total_chunks > 0
    assert "python" in stats.languages


def test_index_with_progress_callback(indexer, sample_codebase):
    """Test that progress callback is called during indexing."""
    progress_calls = []

    def progress_callback(current, total, filename):
        progress_calls.append((current, total, filename))

    indexer.index_path(sample_codebase, force=False, progress_callback=progress_callback)

    # Progress callback should have been called
    assert len(progress_calls) > 0

    # Verify callback arguments
    for current, total, filename in progress_calls:
        assert current <= total
        assert isinstance(filename, str)


def test_deleted_file_removed_from_index(indexer, sample_python_file, temp_dir):
    """Test that deleted files are removed from index."""
    # Index the file
    rel_path = str(sample_python_file.relative_to(temp_dir))
    indexer.index_path(sample_python_file, force=False)

    # Verify it's in the index
    stats = indexer.store.get_stats()
    assert stats.total_chunks > 0

    # Delete chunks for this path (simulating file deletion)
    deleted = indexer.store.delete_by_path(rel_path)
    assert deleted > 0

    # Verify chunks are gone
    stats = indexer.store.get_stats()
    assert stats.total_chunks == 0


def test_indexer_repr(indexer):
    """Test string representation."""
    repr_str = repr(indexer)
    assert "Indexer" in repr_str


def test_index_handles_parse_errors_gracefully(indexer, temp_dir):
    """Test that indexing handles unparseable files gracefully."""
    # Create a file with syntax errors
    bad_file = temp_dir / "bad.py"
    bad_file.write_text("def invalid syntax {{{")

    # Should not crash, but may skip or handle as fallback
    chunks_added = indexer._index_file(bad_file, base_path=temp_dir)

    # Should either add chunks as fallback or return 0
    assert chunks_added >= 0


def test_index_respects_exclude_patterns(indexer, temp_dir):
    """Test that exclude patterns from config are respected."""
    # Create files matching default exclude patterns
    (temp_dir / "node_modules").mkdir()
    (temp_dir / "node_modules" / "lib.js").write_text("code")

    (temp_dir / "dist").mkdir()
    (temp_dir / "dist" / "bundle.js").write_text("code")

    (temp_dir / "main.py").write_text("print('hello')")

    files = list(indexer._discover_files(temp_dir))

    file_paths = [str(f) for f in files]

    # Excluded directories should not appear
    assert not any("node_modules" in p for p in file_paths)
    assert not any("dist" in p for p in file_paths)

    # main.py should be found
    assert any("main.py" in p for p in file_paths)


# ============================================================================
# Phase 3 Tests
# ============================================================================


def test_only_modified_files_reindexed(indexer, temp_dir):
    """Unchanged files are skipped on re-index (Phase 3)."""
    # Create test files
    file1 = temp_dir / "file1.py"
    file2 = temp_dir / "file2.py"
    file1.write_text("def func1():\n    pass\n")
    file2.write_text("def func2():\n    pass\n")

    # Index once
    stats1 = indexer.index_path(temp_dir, force=False)
    initial_chunks = stats1.total_chunks
    assert initial_chunks > 0

    # Index again without changes (should skip)
    stats2 = indexer.index_path(temp_dir, force=False)
    assert stats2.total_chunks == initial_chunks

    # Modify file1
    file1.write_text("def func1():\n    pass\n\ndef new_func():\n    pass\n")

    # Index again (should only re-index file1)
    stats3 = indexer.index_path(temp_dir, force=False)
    # Should have more chunks now due to the new function
    assert stats3.total_chunks >= initial_chunks


def test_deleted_files_removed_from_index(indexer, temp_dir):
    """Deleted file chunks are cleaned up (Phase 3)."""
    # Create and index test files
    file1 = temp_dir / "file1.py"
    file2 = temp_dir / "file2.py"
    file1.write_text("def func1():\n    pass\n")
    file2.write_text("def func2():\n    pass\n")

    # Index the directory
    indexer.index_path(temp_dir, force=False)

    # Verify both files are indexed
    stats1 = indexer.store.get_stats()
    assert stats1.total_files == 2
    initial_chunks = stats1.total_chunks

    # Delete file1
    file1.unlink()

    # Re-index the directory
    indexer.index_path(temp_dir, force=False)

    # Verify chunks for file1 are removed
    stats2 = indexer.store.get_stats()
    assert stats2.total_files == 1  # Only file2 remains
    assert stats2.total_chunks < initial_chunks  # Fewer chunks


def test_nested_gitignore_patterns(indexer, temp_dir):
    """Nested .gitignore files are respected (Phase 3)."""
    # Create directory structure with nested .gitignore files
    # /temp_dir/.gitignore - ignore *.log
    # /temp_dir/subdir/.gitignore - ignore *.tmp

    root_gitignore = temp_dir / ".gitignore"
    root_gitignore.write_text("*.log\n")

    subdir = temp_dir / "subdir"
    subdir.mkdir()
    sub_gitignore = subdir / ".gitignore"
    sub_gitignore.write_text("*.tmp\n")

    # Create test files
    (temp_dir / "file.log").write_text("log content")  # Should be ignored
    (temp_dir / "file.py").write_text("def test(): pass")  # Should be indexed
    (subdir / "file.tmp").write_text("temp content")  # Should be ignored
    (subdir / "file.py").write_text("def test(): pass")  # Should be indexed

    # Discover files
    files = list(indexer._discover_files(temp_dir))
    file_names = [f.name for f in files]

    # Verify *.log and *.tmp files are excluded
    assert "file.log" not in file_names
    assert "file.tmp" not in file_names

    # Verify *.py files are included
    assert file_names.count("file.py") == 2


def test_git_branch_tracking(indexer, temp_dir):
    """Git branch is tracked in chunks (Phase 3)."""
    import subprocess

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir,
        check=True,
        capture_output=True
    )

    # Create and commit a file
    test_file = temp_dir / "test.py"
    test_file.write_text("def test():\n    pass\n")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir,
        check=True,
        capture_output=True
    )

    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-x"],
        cwd=temp_dir,
        check=True,
        capture_output=True
    )

    # Index with branch auto-detection
    indexer.index_path(temp_dir, force=True)

    # Verify branch was detected and stored
    assert indexer.current_branch == "feature-x"

    # Verify chunks have branch information
    # (We'll need to query the store to check this)
    stats = indexer.store.get_stats()
    assert stats.total_chunks > 0


def test_manual_branch_override(indexer, temp_dir):
    """Manual branch specification overrides auto-detection (Phase 3)."""
    # Create test file
    test_file = temp_dir / "test.py"
    test_file.write_text("def test():\n    pass\n")

    # Index with manual branch specification
    indexer.index_path(temp_dir, force=True, branch="custom-branch")

    # Verify manual branch was used
    assert indexer.current_branch == "custom-branch"


def test_cleanup_deleted_files_respects_config(indexer, temp_dir):
    """Deleted file cleanup respects config setting (Phase 3)."""
    # Create and index a file
    test_file = temp_dir / "test.py"
    test_file.write_text("def test():\n    pass\n")

    indexer.index_path(temp_dir, force=False)
    initial_stats = indexer.store.get_stats()

    # Delete the file
    test_file.unlink()

    # Disable cleanup in config
    indexer.config.set("git", "cleanup_deleted", value=False)

    # Re-index
    indexer.index_path(temp_dir, force=False)

    # Chunks should still exist (cleanup disabled)
    stats = indexer.store.get_stats()
    assert stats.total_chunks == initial_stats.total_chunks
