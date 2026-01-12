"""
Progress reporting system for ctxd.

Provides progress tracking with ETA calculation for indexing operations.
"""

import time
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class ProgressEvent:
    """
    Event emitted during indexing progress.

    Attributes:
        current: Number of files processed so far
        total: Total number of files to process
        filename: Current file being processed
        elapsed_seconds: Time elapsed since start
        eta_seconds: Estimated time remaining (None if unknown)
        files_per_second: Processing rate
    """
    current: int
    total: int
    filename: str
    elapsed_seconds: float
    eta_seconds: Optional[float] = None
    files_per_second: float = 0.0


class ProgressReporter:
    """
    Tracks and reports indexing progress with ETA calculation.

    Features:
    - Tracks files processed and total count
    - Calculates files/second processing rate
    - Estimates time remaining (ETA)
    - Emits events via callback for each file processed
    """

    def __init__(self, total_files: int, callback: Optional[Callable[[ProgressEvent], None]] = None):
        """
        Initialize progress reporter.

        Args:
            total_files: Total number of files to process
            callback: Optional callback function to receive ProgressEvents
        """
        self.total_files = total_files
        self.current_file = 0
        self.start_time = time.time()
        self.callback = callback

    def update(self, filename: str) -> ProgressEvent:
        """
        Update progress with next file being processed.

        Args:
            filename: Name of file currently being processed

        Returns:
            ProgressEvent with current statistics
        """
        self.current_file += 1
        elapsed = time.time() - self.start_time

        # Calculate processing rate (avoid division by zero)
        files_per_second = self.current_file / elapsed if elapsed > 0 else 0

        # Estimate time remaining
        remaining_files = self.total_files - self.current_file
        eta = remaining_files / files_per_second if files_per_second > 0 else None

        # Create progress event
        event = ProgressEvent(
            current=self.current_file,
            total=self.total_files,
            filename=filename,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            files_per_second=files_per_second
        )

        # Emit event via callback
        if self.callback:
            self.callback(event)

        return event

    @staticmethod
    def format_eta(seconds: Optional[float]) -> str:
        """
        Format ETA in human-readable form.

        Args:
            seconds: Number of seconds (None if unknown)

        Returns:
            Formatted string like "2m 30s", "1h 15m", or "unknown"
        """
        if seconds is None:
            return "unknown"

        # Convert to integer seconds
        total_secs = int(seconds)

        # Calculate hours, minutes, seconds
        minutes, secs = divmod(total_secs, 60)
        hours, minutes = divmod(minutes, 60)

        # Format based on magnitude
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human-readable form.

        Args:
            seconds: Number of seconds

        Returns:
            Formatted string like "2.5s", "1m 30s", "1h 15m"
        """
        if seconds < 60:
            return f"{seconds:.1f}s"

        total_secs = int(seconds)
        minutes, secs = divmod(total_secs, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {secs}s"

    def get_summary(self) -> str:
        """
        Get a summary of current progress.

        Returns:
            Human-readable progress summary
        """
        elapsed = time.time() - self.start_time
        files_per_second = self.current_file / elapsed if elapsed > 0 else 0

        return (
            f"Processed {self.current_file}/{self.total_files} files "
            f"in {self.format_duration(elapsed)} "
            f"({files_per_second:.1f} files/sec)"
        )
