"""
Tests for git utilities.
"""

import subprocess
from pathlib import Path
import pytest

from ctxd.git_utils import GitUtils


class TestGitUtils:
    """Test suite for GitUtils class."""

    def test_get_current_branch_in_git_repo(self, tmp_path):
        """Detect current git branch in a git repository."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True
        )

        # Create a commit (required to create branch)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True
        )

        # Create and checkout a new branch
        subprocess.run(
            ["git", "checkout", "-b", "feature-x"],
            cwd=tmp_path,
            check=True,
            capture_output=True
        )

        # Test branch detection
        branch = GitUtils.get_current_branch(tmp_path)
        assert branch == "feature-x"

    def test_get_current_branch_non_git_repo(self, tmp_path):
        """Return None for non-git repositories."""
        branch = GitUtils.get_current_branch(tmp_path)
        assert branch is None

    def test_is_git_repo_positive(self, tmp_path):
        """Detect if directory is a git repo (positive case)."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

        assert GitUtils.is_git_repo(tmp_path) is True

    def test_is_git_repo_negative(self, tmp_path):
        """Detect if directory is not a git repo (negative case)."""
        assert GitUtils.is_git_repo(tmp_path) is False

    def test_is_git_repo_subdirectory(self, tmp_path):
        """Detect git repo from subdirectory."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Should still detect as git repo
        assert GitUtils.is_git_repo(subdir) is True

    def test_load_nested_gitignore(self, tmp_path):
        """Load and merge nested .gitignore files."""
        # Create directory structure with nested .gitignore files
        # /tmp_path/.gitignore - ignore *.log
        # /tmp_path/subdir/.gitignore - ignore *.tmp

        root_gitignore = tmp_path / ".gitignore"
        root_gitignore.write_text("*.log\n")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        sub_gitignore = subdir / ".gitignore"
        sub_gitignore.write_text("*.tmp\n")

        # Load nested gitignore
        spec = GitUtils.load_nested_gitignore(tmp_path)
        assert spec is not None

        # Test that patterns from both files are respected
        assert spec.match_file("test.log") is True  # Root gitignore
        assert spec.match_file("subdir/test.tmp") is True  # Subdir gitignore
        assert spec.match_file("test.py") is False  # Not ignored

    def test_load_nested_gitignore_no_files(self, tmp_path):
        """Return None when no .gitignore files exist."""
        spec = GitUtils.load_nested_gitignore(tmp_path)
        assert spec is None

    def test_load_nested_gitignore_directory_scoping(self, tmp_path):
        """Nested gitignore patterns are scoped to their directory."""
        # Create structure:
        # /tmp_path/subdir/.gitignore - ignore test.txt
        # This should only ignore test.txt in subdir/, not root/

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        sub_gitignore = subdir / ".gitignore"
        sub_gitignore.write_text("test.txt\n")

        spec = GitUtils.load_nested_gitignore(tmp_path)
        assert spec is not None

        # test.txt in subdir should be ignored
        assert spec.match_file("subdir/test.txt") is True

        # test.txt in root should NOT be ignored (scoping)
        # NOTE: This test validates that our scoping is working
        assert spec.match_file("test.txt") is False

    def test_get_git_root(self, tmp_path):
        """Get the root directory of a git repository."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

        # Create subdirectory
        subdir = tmp_path / "deep" / "nested" / "dir"
        subdir.mkdir(parents=True)

        # Get git root from subdirectory
        git_root = GitUtils.get_git_root(subdir)
        assert git_root == tmp_path.resolve()

    def test_get_git_root_non_repo(self, tmp_path):
        """Return None for non-git repositories."""
        git_root = GitUtils.get_git_root(tmp_path)
        assert git_root is None

    def test_load_gitignore_with_comments_and_blank_lines(self, tmp_path):
        """Handle .gitignore files with comments and blank lines."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""
# This is a comment
*.log

# Another comment
*.tmp
        """)

        spec = GitUtils.load_nested_gitignore(tmp_path)
        assert spec is not None

        # Should still match patterns, ignoring comments
        assert spec.match_file("test.log") is True
        assert spec.match_file("test.tmp") is True
