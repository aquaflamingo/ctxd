"""
Pytest fixtures for ctxd tests.

Provides reusable test fixtures for temporary directories, sample files,
mock components, and test data.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from ctxd.config import Config
from ctxd.embeddings import EmbeddingModel
from ctxd.store import VectorStore
from ctxd.indexer import Indexer


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file with functions and classes."""
    python_code = '''"""Sample Python module for testing."""

def hello_world():
    """Print hello world."""
    print("Hello, World!")
    return "Hello"

class Calculator:
    """A simple calculator class."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtract b from a."""
        return a - b

@property
def complex_function(x, y, z):
    """A more complex function with decorators."""
    result = x + y + z
    if result > 10:
        return result * 2
    return result
'''
    file_path = temp_dir / "sample.py"
    file_path.write_text(python_code)
    return file_path


@pytest.fixture
def sample_markdown_file(temp_dir):
    """Create a sample Markdown file."""
    markdown_content = '''# Sample Document

This is a sample markdown document for testing.

## Section 1

This is the first section with some content.
It has multiple lines.

## Section 2

This is the second section.

### Subsection 2.1

Some nested content here.
'''
    file_path = temp_dir / "README.md"
    file_path.write_text(markdown_content)
    return file_path


@pytest.fixture
def sample_gitignore(temp_dir):
    """Create a sample .gitignore file."""
    gitignore_content = '''# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# Node
node_modules/
dist/
build/

# IDE
.vscode/
.idea/
'''
    file_path = temp_dir / ".gitignore"
    file_path.write_text(gitignore_content)
    return file_path


@pytest.fixture
def sample_codebase(temp_dir, sample_python_file, sample_markdown_file):
    """Create a small sample codebase with multiple files."""
    # Create subdirectory structure
    src_dir = temp_dir / "src"
    src_dir.mkdir()

    # Add more Python files
    (src_dir / "utils.py").write_text('''
def utility_function():
    """A utility function."""
    return "utility"
''')

    (src_dir / "main.py").write_text('''
from utils import utility_function

def main():
    """Main entry point."""
    print(utility_function())

if __name__ == "__main__":
    main()
''')

    # Create a tests directory (should be indexed too)
    tests_dir = temp_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_utils.py").write_text('''
def test_utility():
    """Test utility function."""
    assert True
''')

    return temp_dir


@pytest.fixture
def config(temp_dir):
    """Create a test configuration."""
    return Config(project_root=temp_dir)


@pytest.fixture
def embedding_model():
    """Create an embedding model for testing."""
    # Use a smaller model for faster tests
    return EmbeddingModel(model_name="all-MiniLM-L6-v2")


@pytest.fixture
def vector_store(temp_dir):
    """Create a vector store for testing."""
    db_path = temp_dir / ".ctxd" / "data.lance"
    return VectorStore(db_path)


@pytest.fixture
def indexer(vector_store, embedding_model, config):
    """Create an indexer for testing."""
    return Indexer(vector_store, embedding_model, config)


@pytest.fixture
def sample_embeddings():
    """Sample embedding vectors for testing."""
    return [
        [0.1, 0.2, 0.3] * 128,  # 384-dim vector
        [0.2, 0.3, 0.4] * 128,
        [0.3, 0.4, 0.5] * 128,
    ]
