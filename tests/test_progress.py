"""
Tests for progress reporting.
"""

import time
import pytest

from ctxd.progress import ProgressReporter, ProgressEvent


class TestProgressReporter:
    """Test suite for ProgressReporter class."""

    def test_progress_reporter_initialization(self):
        """ProgressReporter initializes correctly."""
        reporter = ProgressReporter(total_files=100)

        assert reporter.total_files == 100
        assert reporter.current_file == 0
        assert reporter.callback is None

    def test_progress_reporter_update(self):
        """Progress reporter updates correctly."""
        reporter = ProgressReporter(total_files=10)

        # Update progress
        event = reporter.update("file1.py")

        assert event.current == 1
        assert event.total == 10
        assert event.filename == "file1.py"
        assert event.elapsed_seconds > 0

    def test_progress_reporter_eta_calculation(self):
        """Progress reporter calculates ETA correctly."""
        reporter = ProgressReporter(total_files=100)

        # Process some files with a small delay
        for i in range(10):
            reporter.update(f"file{i}.py")
            time.sleep(0.01)  # Small delay to simulate processing

        # ETA should be calculated
        event = reporter.update("file10.py")
        assert event.eta_seconds is not None
        assert event.eta_seconds > 0
        assert event.files_per_second > 0

    def test_progress_reporter_eta_at_completion(self):
        """ETA is zero when all files are processed."""
        reporter = ProgressReporter(total_files=5)

        # Process all files
        for i in range(5):
            event = reporter.update(f"file{i}.py")

        # At completion, ETA should be 0
        assert event.eta_seconds == 0

    def test_progress_event_callback(self):
        """Progress reporter emits events via callback."""
        events = []

        def callback(event: ProgressEvent):
            events.append(event)

        reporter = ProgressReporter(total_files=5, callback=callback)

        # Process files
        for i in range(5):
            reporter.update(f"file{i}.py")

        # Verify callback was called for each update
        assert len(events) == 5
        assert all(isinstance(e, ProgressEvent) for e in events)

        # Verify event progression
        assert events[0].current == 1
        assert events[4].current == 5

    def test_format_eta_seconds(self):
        """Format ETA correctly for seconds only."""
        eta_str = ProgressReporter.format_eta(45)
        assert eta_str == "45s"

    def test_format_eta_minutes_seconds(self):
        """Format ETA correctly for minutes and seconds."""
        eta_str = ProgressReporter.format_eta(125)  # 2m 5s
        assert eta_str == "2m 5s"

    def test_format_eta_hours_minutes(self):
        """Format ETA correctly for hours and minutes."""
        eta_str = ProgressReporter.format_eta(3665)  # 1h 1m
        assert eta_str == "1h 1m"

    def test_format_eta_none(self):
        """Format ETA as 'unknown' when None."""
        eta_str = ProgressReporter.format_eta(None)
        assert eta_str == "unknown"

    def test_format_duration_seconds(self):
        """Format duration correctly for seconds."""
        duration_str = ProgressReporter.format_duration(5.7)
        assert duration_str == "5.7s"

    def test_format_duration_minutes(self):
        """Format duration correctly for minutes."""
        duration_str = ProgressReporter.format_duration(125)  # 2m 5s
        assert duration_str == "2m 5s"

    def test_format_duration_hours(self):
        """Format duration correctly for hours."""
        duration_str = ProgressReporter.format_duration(3665)  # 1h 1m
        assert duration_str == "1h 1m"

    def test_get_summary(self):
        """Get progress summary string."""
        reporter = ProgressReporter(total_files=100)

        # Process some files
        for i in range(25):
            reporter.update(f"file{i}.py")
            time.sleep(0.001)  # Tiny delay

        summary = reporter.get_summary()

        # Summary should contain key information
        assert "25/100" in summary
        assert "files" in summary

    def test_progress_event_fields(self):
        """ProgressEvent contains all required fields."""
        reporter = ProgressReporter(total_files=10)
        event = reporter.update("test.py")

        # Verify all fields are present
        assert hasattr(event, "current")
        assert hasattr(event, "total")
        assert hasattr(event, "filename")
        assert hasattr(event, "elapsed_seconds")
        assert hasattr(event, "eta_seconds")
        assert hasattr(event, "files_per_second")

    def test_files_per_second_calculation(self):
        """Files per second is calculated correctly."""
        reporter = ProgressReporter(total_files=100)

        # Process files with controlled timing
        start_time = time.time()
        for i in range(10):
            reporter.update(f"file{i}.py")

        elapsed = time.time() - start_time
        event = reporter.update("file10.py")

        # Files per second should be approximately 11 / elapsed
        expected_rate = 11 / elapsed
        assert abs(event.files_per_second - expected_rate) < 1.0  # Within 1 file/sec tolerance
