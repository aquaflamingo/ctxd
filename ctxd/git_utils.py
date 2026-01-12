"""
Git integration utilities for ctxd.

Provides utilities for git operations without external dependencies.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional
import pathspec

logger = logging.getLogger(__name__)


class GitUtils:
    """
    Git integration utilities.

    Provides methods for:
    - Detecting git repositories
    - Getting current branch
    - Loading nested .gitignore files
    """

    @staticmethod
    def get_current_branch(repo_path: Path) -> Optional[str]:
        """
        Detect current git branch using subprocess.

        Args:
            repo_path: Path to check for git repository

        Returns:
            Branch name if in a git repo, None otherwise
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            branch = result.stdout.strip()

            # Handle detached HEAD state
            if branch == "HEAD":
                # Try to get commit SHA
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True
                )
                return f"detached-{result.stdout.strip()}"

            logger.debug(f"Detected git branch: {branch}")
            return branch

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            logger.debug(f"Not a git repository or git not available: {repo_path}")
            return None
        except Exception as e:
            logger.warning(f"Failed to detect git branch: {e}")
            return None

    @staticmethod
    def is_git_repo(path: Path) -> bool:
        """
        Check if path is inside a git repository.

        Args:
            path: Path to check

        Returns:
            True if inside a git repository, False otherwise
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                timeout=5,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
        except Exception as e:
            logger.warning(f"Error checking git repository: {e}")
            return False

    @staticmethod
    def load_nested_gitignore(root_path: Path) -> Optional[pathspec.PathSpec]:
        """
        Load and merge all .gitignore files in directory tree.

        This method walks the directory tree and collects patterns from all
        .gitignore files, properly handling directory-scoped patterns.

        Args:
            root_path: Root directory to search for .gitignore files

        Returns:
            PathSpec object with merged patterns, or None if no .gitignore files found
        """
        all_patterns = []
        gitignore_files = []

        # Find all .gitignore files
        for path in root_path.rglob(".gitignore"):
            if path.is_file():
                gitignore_files.append(path)

        # Also check root .gitignore explicitly
        root_gitignore = root_path / ".gitignore"
        if root_gitignore.exists() and root_gitignore not in gitignore_files:
            gitignore_files.append(root_gitignore)

        if not gitignore_files:
            logger.debug("No .gitignore files found")
            return None

        logger.debug(f"Found {len(gitignore_files)} .gitignore file(s)")

        # Load patterns from each .gitignore
        for gitignore_path in gitignore_files:
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    patterns = f.read().splitlines()

                # Get directory containing this .gitignore
                gitignore_dir = gitignore_path.parent.relative_to(root_path)

                # Prefix patterns with directory path if not in root
                if str(gitignore_dir) != ".":
                    # Scope patterns to the directory
                    scoped_patterns = []
                    for pattern in patterns:
                        # Skip empty lines and comments
                        if not pattern.strip() or pattern.strip().startswith("#"):
                            scoped_patterns.append(pattern)
                            continue

                        # Handle negation patterns
                        if pattern.startswith("!"):
                            scoped_patterns.append(f"!{gitignore_dir}/{pattern[1:]}")
                        else:
                            # Scope pattern to directory
                            scoped_patterns.append(f"{gitignore_dir}/{pattern}")

                    all_patterns.extend(scoped_patterns)
                else:
                    all_patterns.extend(patterns)

                logger.debug(f"Loaded {len(patterns)} patterns from {gitignore_path}")

            except Exception as e:
                logger.warning(f"Failed to parse {gitignore_path}: {e}")
                continue

        if not all_patterns:
            return None

        try:
            # Create PathSpec from all collected patterns
            spec = pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)
            logger.info(f"Loaded {len(all_patterns)} total patterns from {len(gitignore_files)} .gitignore files")
            return spec
        except Exception as e:
            logger.error(f"Failed to create PathSpec from gitignore patterns: {e}")
            return None

    @staticmethod
    def get_git_root(path: Path) -> Optional[Path]:
        """
        Get the root directory of the git repository.

        Args:
            path: Path inside a git repository

        Returns:
            Path to git root, or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None
        except Exception as e:
            logger.warning(f"Error getting git root: {e}")
            return None
