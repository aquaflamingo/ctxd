"""
Result enhancement module for ctxd.

Provides de-duplication, context expansion, and recency ranking
to improve search result quality.
"""

import logging
from pathlib import Path
from typing import Optional

from .models import SearchResult, CodeChunk

logger = logging.getLogger(__name__)


class ResultEnhancer:
    """
    Enhances search results with de-duplication, context expansion,
    and recency-based re-ranking.
    """

    def deduplicate(
        self,
        results: list[SearchResult],
        overlap_threshold: float = 0.5
    ) -> list[SearchResult]:
        """
        Remove overlapping chunks from the same file.

        When multiple chunks from the same file overlap by more than
        the threshold percentage, keep only the highest-scoring chunk.

        Args:
            results: List of search results
            overlap_threshold: Overlap percentage threshold (0.0-1.0)

        Returns:
            De-duplicated list of search results
        """
        if not results:
            return results

        # Group results by file path
        by_file = {}
        for result in results:
            path = result.chunk.path
            if path not in by_file:
                by_file[path] = []
            by_file[path].append(result)

        # De-duplicate within each file
        deduplicated = []
        for path, file_results in by_file.items():
            # Sort by score (highest first)
            file_results.sort(key=lambda r: r.score, reverse=True)

            kept = []
            for result in file_results:
                # Check if this result overlaps with any already kept
                overlaps = False
                for kept_result in kept:
                    overlap = self._calculate_overlap(
                        result.chunk.start_line, result.chunk.end_line,
                        kept_result.chunk.start_line, kept_result.chunk.end_line
                    )
                    if overlap >= overlap_threshold:
                        overlaps = True
                        break

                if not overlaps:
                    kept.append(result)

            deduplicated.extend(kept)

        # Re-sort by score
        deduplicated.sort(key=lambda r: r.score, reverse=True)

        logger.debug(f"De-duplication: {len(results)} → {len(deduplicated)} results")
        return deduplicated

    def expand_context(
        self,
        results: list[SearchResult],
        lines_before: int = 3,
        lines_after: int = 3,
        project_root: Optional[Path] = None
    ) -> list[SearchResult]:
        """
        Include surrounding lines from source file for better context.

        Reads the actual source file and expands the chunk to include
        lines before and after the original chunk.

        Args:
            results: List of search results
            lines_before: Number of lines to include before chunk
            lines_after: Number of lines to include after chunk
            project_root: Root directory of the project

        Returns:
            Search results with expanded context
        """
        if not results or not project_root:
            return results

        expanded = []
        for result in results:
            try:
                # Construct full file path
                file_path = project_root / result.chunk.path

                if not file_path.exists():
                    # Keep original if file not found
                    expanded.append(result)
                    continue

                # Read the file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # Calculate expanded range
                start_line = max(1, result.chunk.start_line - lines_before)
                end_line = min(len(lines), result.chunk.end_line + lines_after)

                # Extract expanded text (convert to 0-indexed)
                expanded_text = ''.join(lines[start_line - 1:end_line])

                # Create new chunk with expanded context
                expanded_chunk = CodeChunk(
                    text=expanded_text,
                    path=result.chunk.path,
                    start_line=start_line,
                    end_line=end_line,
                    language=result.chunk.language,
                    chunk_type=result.chunk.chunk_type,
                    name=result.chunk.name,
                    vector=result.chunk.vector,  # 'vector' not 'embedding'
                    file_hash=result.chunk.file_hash,
                    indexed_at=result.chunk.indexed_at,
                    branch=result.chunk.branch
                )

                expanded.append(SearchResult(chunk=expanded_chunk, score=result.score))

            except Exception as e:
                logger.warning(f"Failed to expand context for {result.chunk.path}: {e}")
                # Keep original on error
                expanded.append(result)

        return expanded

    def rerank_by_recency(
        self,
        results: list[SearchResult],
        recency_weight: float = 0.1
    ) -> list[SearchResult]:
        """
        Apply recency boosting for tie-breaking between similar scores.

        Boosts scores based on how recently the chunk was indexed:
        final_score = similarity + (recency_weight * normalized_recency)

        Args:
            results: List of search results
            recency_weight: Weight for recency boost (0.0-1.0)

        Returns:
            Re-ranked search results
        """
        if not results or recency_weight == 0.0:
            return results

        # Find min/max timestamps for normalization
        timestamps = [r.chunk.indexed_at for r in results]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        # Avoid division by zero
        ts_range = max_ts - min_ts
        if ts_range == 0:
            return results

        # Apply recency boost
        reranked = []
        for result in results:
            # Normalize timestamp to 0-1 (1 = most recent)
            normalized_recency = (result.chunk.indexed_at - min_ts) / ts_range

            # Boost score (cap at 1.0 to respect score constraints)
            boosted_score = min(1.0, result.score + (recency_weight * normalized_recency))

            reranked.append(SearchResult(chunk=result.chunk, score=boosted_score))

        # Re-sort by boosted score
        reranked.sort(key=lambda r: r.score, reverse=True)

        return reranked

    @staticmethod
    def _calculate_overlap(start1: int, end1: int, start2: int, end2: int) -> float:
        """
        Calculate percentage overlap between two line ranges.

        Args:
            start1: Start line of first range
            end1: End line of first range
            start2: Start line of second range
            end2: End line of second range

        Returns:
            Overlap percentage (0.0-1.0)
        """
        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start > overlap_end:
            # No overlap
            return 0.0

        overlap_lines = overlap_end - overlap_start + 1

        # Calculate as percentage of smaller range
        range1_lines = end1 - start1 + 1
        range2_lines = end2 - start2 + 1
        smaller_range = min(range1_lines, range2_lines)

        return overlap_lines / smaller_range if smaller_range > 0 else 0.0
