"""
File system watcher for ctxd.

Monitors directories for changes and triggers incremental indexing.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .indexer import Indexer

logger = logging.getLogger(__name__)


class CodeChangeHandler(FileSystemEventHandler):
    """
    Event handler for code file changes.

    Batches changes and debounces rapid modifications to avoid
    excessive re-indexing.
    """

    def __init__(
        self,
        indexer: Indexer,
        debounce_seconds: float = 0.1,
        on_change: Optional[Callable] = None
    ):
        """
        Initialize the change handler.

        Args:
            indexer: Indexer instance to use for re-indexing
            debounce_seconds: Time to wait before processing changes
            on_change: Optional callback when changes are detected
        """
        super().__init__()
        self.indexer = indexer
        self.debounce_seconds = debounce_seconds
        self.on_change = on_change

        # Track pending changes
        self._pending_changes: dict[str, str] = {}  # path -> event_type
        self._last_event_time = 0

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return
        self._queue_change(event.src_path, "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        self._queue_change(event.src_path, "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if event.is_directory:
            return
        self._queue_change(event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events."""
        if event.is_directory:
            return
        # Treat move as delete + create
        self._queue_change(event.src_path, "deleted")
        if hasattr(event, "dest_path"):
            self._queue_change(event.dest_path, "created")

    def _queue_change(self, path: str, event_type: str) -> None:
        """
        Queue a file change for processing.

        Args:
            path: File path that changed
            event_type: Type of event (modified, created, deleted)
        """
        file_path = Path(path)

        # Check if we should index this file
        if not self.indexer.should_index_file(file_path):
            return

        self._pending_changes[path] = event_type
        self._last_event_time = time.time()

        logger.debug(f"Queued {event_type} event for {path}")

        # Notify callback
        if self.on_change:
            self.on_change(path, event_type)

    def process_pending_changes(self) -> None:
        """
        Process all pending changes if debounce period has elapsed.

        This should be called periodically (e.g., in a loop).
        """
        if not self._pending_changes:
            return

        # Check if debounce period has elapsed
        if time.time() - self._last_event_time < self.debounce_seconds:
            return

        logger.info(f"Processing {len(self._pending_changes)} pending changes")

        for path, event_type in list(self._pending_changes.items()):
            try:
                if event_type == "deleted":
                    # Remove from index
                    self.indexer.store.delete_by_path(path)
                    logger.info(f"Removed deleted file from index: {path}")
                else:
                    # Re-index the file (modified or created)
                    file_path = Path(path)
                    if file_path.exists():
                        base_path = file_path.parent
                        self.indexer._index_file(file_path, base_path=base_path)
                        logger.info(f"Re-indexed {event_type} file: {path}")
            except Exception as e:
                logger.error(f"Failed to process change for {path}: {e}")

        # Clear processed changes
        self._pending_changes.clear()


class FileWatcher:
    """
    File system watcher that monitors a directory for changes.

    Uses watchdog to detect file system events and triggers
    incremental indexing for changed files.
    """

    def __init__(self, indexer: Indexer):
        """
        Initialize the file watcher.

        Args:
            indexer: Indexer instance to use for incremental indexing
        """
        self.indexer = indexer
        self.observer: Optional[Observer] = None
        self.handler: Optional[CodeChangeHandler] = None
        self._running = False

    def start(self, path: Path, on_change: Optional[Callable] = None) -> None:
        """
        Start watching a directory for changes.

        Args:
            path: Directory path to watch
            on_change: Optional callback(path, event_type) for change notifications
        """
        if self._running:
            logger.warning("Watcher is already running")
            return

        path = Path(path).resolve()
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        logger.info(f"Starting file watcher for {path}")

        # Create handler and observer
        self.handler = CodeChangeHandler(
            self.indexer,
            debounce_seconds=0.1,
            on_change=on_change
        )
        self.observer = Observer()
        self.observer.schedule(self.handler, str(path), recursive=True)

        # Start observer
        self.observer.start()
        self._running = True

        logger.info("File watcher started")

        # Processing loop
        try:
            while self._running:
                time.sleep(0.1)  # Check every 100ms
                if self.handler:
                    self.handler.process_pending_changes()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the file watcher."""
        if not self._running:
            return

        logger.info("Stopping file watcher")
        self._running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        self.handler = None
        logger.info("File watcher stopped")

    @property
    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running

    def __repr__(self) -> str:
        """String representation."""
        status = "running" if self._running else "stopped"
        return f"FileWatcher({status})"
