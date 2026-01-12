"""
Configuration management for ctxd.

Provides default configuration and loading from .ctxd/config.toml.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python versions

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    "indexer": {
        "exclude": [
            "node_modules",
            "*.min.js",
            "dist",
            "build",
            ".venv",
            "venv",
            "__pycache__",
            "*.pyc",
            ".git",
            ".ctxd",
            ".ctxcache",
        ],
        "include": [],
        "max_file_size": 1048576,  # 1MB
        "max_chunk_size": 500,
        "chunk_overlap": 50,
    },
    "embeddings": {
        "model": "all-MiniLM-L6-v2",
        "batch_size": 32,
    },
    "search": {
        "default_limit": 10,
        "min_score": 0.3,
        # Phase 4: Hybrid search
        "mode": "hybrid",           # "vector", "fts", "hybrid"
        "fts_weight": 0.5,          # BM25 weight (0.0-1.0)
        # Phase 4: Result enhancement
        "deduplicate": True,
        "overlap_threshold": 0.5,
        "expand_context": False,
        "context_lines_before": 3,
        "context_lines_after": 3,
        "recency_weight": 0.1,
    },
}


class Config:
    """
    Configuration manager for ctxd.

    Loads configuration from .ctxd/config.toml if it exists,
    otherwise uses defaults.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            project_root: Root directory of the project (defaults to current directory)
        """
        self.project_root = project_root or Path.cwd()
        self.config_path = self.project_root / ".ctxd" / "config.toml"
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or use defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "rb") as f:
                    user_config = tomllib.load(f)
                logger.info(f"Loaded config from {self.config_path}")
                # Merge with defaults (user config takes precedence)
                return self._merge_configs(DEFAULT_CONFIG, user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
                logger.warning("Using default configuration")
                return DEFAULT_CONFIG.copy()
        else:
            logger.debug("No config file found, using defaults")
            return DEFAULT_CONFIG.copy()

    def _merge_configs(self, default: dict, user: dict) -> dict:
        """
        Recursively merge user config with defaults.

        User values take precedence, but missing keys use defaults.
        """
        merged = default.copy()
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by nested keys.

        Examples:
            config.get("indexer", "max_file_size")
            config.get("embeddings", "model")

        Args:
            *keys: Nested keys to traverse
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys: str, value: Any) -> None:
        """
        Set a configuration value by nested keys.

        Args:
            *keys: Nested keys to traverse
            value: Value to set
        """
        if not keys:
            return

        # Navigate to the parent dict
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value

    @property
    def indexer(self) -> dict[str, Any]:
        """Get indexer configuration."""
        return self._config.get("indexer", {})

    @property
    def embeddings(self) -> dict[str, Any]:
        """Get embeddings configuration."""
        return self._config.get("embeddings", {})

    @property
    def search(self) -> dict[str, Any]:
        """Get search configuration."""
        return self._config.get("search", {})

    def __repr__(self) -> str:
        """String representation."""
        return f"Config(project_root={self.project_root})"
