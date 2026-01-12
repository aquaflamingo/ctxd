"""
Unit tests for the result enhancer.

Tests de-duplication, context expansion, and recency ranking.
"""

import pytest
from pathlib import Path
from ctxd.models import CodeChunk, SearchResult
from ctxd.result_enhancer import ResultEnhancer


@pytest.fixture
def enhancer():
    """Create a ResultEnhancer instance."""
    return ResultEnhancer()


@pytest.fixture
def sample_results():
    """Create sample search results for testing."""
    return [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="def function1():\n    pass",
                path="test.py",
                start_line=1,
                end_line=2,
                chunk_type="function",
                name="function1",
                language="python",
                file_hash="hash1",
                indexed_at=1000.0,
            ),
            score=0.9
        ),
        SearchResult(
            chunk=CodeChunk(
                vector=[0.2] * 384,
                text="def function2():\n    pass",
                path="test.py",
                start_line=10,
                end_line=11,
                chunk_type="function",
                name="function2",
                language="python",
                file_hash="hash1",
                indexed_at=2000.0,
            ),
            score=0.8
        ),
    ]


def test_calculate_overlap_no_overlap(enhancer):
    """Test overlap calculation with no overlap."""
    overlap = enhancer._calculate_overlap(1, 5, 10, 15)
    assert overlap == 0.0


def test_calculate_overlap_partial(enhancer):
    """Test overlap calculation with partial overlap."""
    # Lines 1-10 and 5-15 overlap on lines 5-10 (6 lines)
    # Smaller range is 10 lines, so overlap is 6/10 = 0.6
    overlap = enhancer._calculate_overlap(1, 10, 5, 15)
    assert overlap == 0.6


def test_calculate_overlap_complete(enhancer):
    """Test overlap calculation with complete overlap."""
    # Same range
    overlap = enhancer._calculate_overlap(1, 10, 1, 10)
    assert overlap == 1.0

    # One range contains the other
    overlap = enhancer._calculate_overlap(1, 20, 5, 10)
    assert overlap == 1.0  # Smaller range (5-10) is 100% contained


def test_deduplicate_no_overlaps(enhancer, sample_results):
    """Test de-duplication with no overlapping chunks."""
    # Results are far apart (lines 1-2 and 10-11)
    result = enhancer.deduplicate(sample_results, overlap_threshold=0.5)

    # Should keep all results
    assert len(result) == 2


def test_deduplicate_with_overlaps(enhancer):
    """Test de-duplication removes overlapping chunks."""
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="lines 1-10",
                path="test.py",
                start_line=1,
                end_line=10,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
            ),
            score=0.9
        ),
        SearchResult(
            chunk=CodeChunk(
                vector=[0.2] * 384,
                text="lines 5-15",
                path="test.py",
                start_line=5,
                end_line=15,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
            ),
            score=0.8
        ),
    ]

    enhancer_inst = ResultEnhancer()
    result = enhancer_inst.deduplicate(results, overlap_threshold=0.5)

    # Should keep only the higher-scoring result (0.9)
    assert len(result) == 1
    assert result[0].score == 0.9


def test_deduplicate_different_files(enhancer):
    """Test de-duplication keeps overlaps from different files."""
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="lines 1-10",
                path="file1.py",
                start_line=1,
                end_line=10,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
            ),
            score=0.9
        ),
        SearchResult(
            chunk=CodeChunk(
                vector=[0.2] * 384,
                text="lines 1-10",
                path="file2.py",
                start_line=1,
                end_line=10,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash2",
            ),
            score=0.8
        ),
    ]

    enhancer_inst = ResultEnhancer()
    result = enhancer_inst.deduplicate(results, overlap_threshold=0.5)

    # Should keep both (different files)
    assert len(result) == 2


def test_deduplicate_empty_list(enhancer):
    """Test de-duplication with empty list."""
    result = enhancer.deduplicate([], overlap_threshold=0.5)
    assert len(result) == 0


def test_expand_context(enhancer, temp_dir):
    """Test context expansion with surrounding lines."""
    # Create a test file
    test_file = temp_dir / "test.py"
    content = "\n".join([f"line {i}" for i in range(1, 21)])
    test_file.write_text(content)

    # Create a result for lines 10-12
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="line 10\nline 11\nline 12",
                path="test.py",
                start_line=10,
                end_line=12,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
            ),
            score=0.9
        ),
    ]

    # Expand with 2 lines before and after
    expanded = enhancer.expand_context(
        results,
        lines_before=2,
        lines_after=2,
        project_root=temp_dir
    )

    # Should now include lines 8-14
    assert len(expanded) == 1
    assert expanded[0].chunk.start_line == 8
    assert expanded[0].chunk.end_line == 14
    assert "line 8" in expanded[0].chunk.text
    assert "line 14" in expanded[0].chunk.text


def test_expand_context_file_not_found(enhancer, temp_dir):
    """Test context expansion when file doesn't exist."""
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="content",
                path="nonexistent.py",
                start_line=1,
                end_line=1,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
            ),
            score=0.9
        ),
    ]

    # Should keep original when file not found
    expanded = enhancer.expand_context(
        results,
        lines_before=3,
        lines_after=3,
        project_root=temp_dir
    )

    assert len(expanded) == 1
    assert expanded[0].chunk.text == "content"


def test_expand_context_at_file_boundaries(enhancer, temp_dir):
    """Test context expansion at start/end of file."""
    # Create a small test file
    test_file = temp_dir / "test.py"
    test_file.write_text("line 1\nline 2\nline 3")

    # Test expansion at start (should not go below line 1)
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="line 1",
                path="test.py",
                start_line=1,
                end_line=1,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
            ),
            score=0.9
        ),
    ]

    expanded = enhancer.expand_context(
        results,
        lines_before=10,
        lines_after=1,
        project_root=temp_dir
    )

    assert expanded[0].chunk.start_line == 1
    assert expanded[0].chunk.end_line == 2


def test_rerank_by_recency(enhancer):
    """Test recency-based re-ranking."""
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="old chunk",
                path="test.py",
                start_line=1,
                end_line=1,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
                indexed_at=1000.0,
            ),
            score=0.8
        ),
        SearchResult(
            chunk=CodeChunk(
                vector=[0.2] * 384,
                text="new chunk",
                path="test.py",
                start_line=10,
                end_line=10,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
                indexed_at=5000.0,  # More recent
            ),
            score=0.8
        ),
    ]

    enhancer_inst = ResultEnhancer()
    reranked = enhancer_inst.rerank_by_recency(results, recency_weight=0.5)

    # More recent chunk should now rank higher
    assert reranked[0].chunk.text == "new chunk"
    assert reranked[0].score > results[0].score


def test_rerank_by_recency_no_change(enhancer, sample_results):
    """Test recency re-ranking with zero weight."""
    original_order = [r.chunk.name for r in sample_results]

    reranked = enhancer.rerank_by_recency(sample_results, recency_weight=0.0)

    # Order should not change
    assert [r.chunk.name for r in reranked] == original_order


def test_rerank_by_recency_same_timestamp(enhancer):
    """Test recency re-ranking with same timestamps."""
    results = [
        SearchResult(
            chunk=CodeChunk(
                vector=[0.1] * 384,
                text="chunk1",
                path="test.py",
                start_line=1,
                end_line=1,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
                indexed_at=1000.0,
            ),
            score=0.9
        ),
        SearchResult(
            chunk=CodeChunk(
                vector=[0.2] * 384,
                text="chunk2",
                path="test.py",
                start_line=10,
                end_line=10,
                chunk_type="block",
                name=None,
                language="python",
                file_hash="hash1",
                indexed_at=1000.0,  # Same timestamp
            ),
            score=0.8
        ),
    ]

    enhancer_inst = ResultEnhancer()
    reranked = enhancer_inst.rerank_by_recency(results, recency_weight=0.1)

    # Should maintain original order (no timestamp difference)
    assert len(reranked) == 2


def test_rerank_by_recency_empty_list(enhancer):
    """Test recency re-ranking with empty list."""
    result = enhancer.rerank_by_recency([], recency_weight=0.1)
    assert len(result) == 0
