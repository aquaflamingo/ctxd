# Installation Guide

This guide will help you install ctxd on your system.

## Prerequisites

### Required
- Python 3.10 or higher
- pip or uv (recommended)

### Optional
- Git (for repository integration features)
- CUDA-capable GPU (for faster embedding generation, CPU works fine)

## Installation Methods

### Method 1: Using uv (Recommended)

`uv` is a fast Python package manager. This is the recommended installation method for ctxd development.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/ctxd.git
cd ctxd

# Install ctxd with uv
uv pip install -e .

# Verify installation
ctxd --help
```

### Method 2: Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/ctxd.git
cd ctxd

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install ctxd
pip install -e .

# Verify installation
ctxd --help
```

### Method 3: Install from PyPI (Coming Soon)

Once ctxd is published to PyPI, you'll be able to install it with:

```bash
pip install ctxd
```

## Development Installation

If you want to contribute to ctxd or run tests, install the development dependencies:

```bash
# Using uv
uv pip install -e ".[dev]"

# Using pip
pip install -e ".[dev]"
```

This installs additional packages:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async testing support

## Verify Installation

After installation, verify that ctxd is working correctly:

```bash
# Check version
ctxd --version

# View help
ctxd --help

# You should see commands like: init, index, search, status, clean
```

## What Gets Installed

The installation includes:

### Core Commands
- `ctxd` - Main CLI tool
- `ctxd-mcp` - MCP server for Claude Code integration

### Python Package
- `ctxd` package with all modules and dependencies

### Dependencies
The following packages will be automatically installed:

**Vector Database & Search**:
- lancedb - Local vector database
- pylance - Python bindings for Lance

**Embeddings & ML**:
- sentence-transformers - Local embedding models
- torch - PyTorch (required by sentence-transformers)

**Code Parsing**:
- tree-sitter - AST parsing
- tree-sitter-python, tree-sitter-javascript, tree-sitter-typescript, tree-sitter-go - Language grammars

**File System & Git**:
- watchdog - File system watching
- pathspec - .gitignore pattern matching

**CLI & UX**:
- click - CLI framework
- rich - Beautiful terminal output

**Data & Config**:
- pydantic - Data validation
- pandas - Data processing
- tomli - TOML parsing (Python <3.11)

**MCP Integration**:
- mcp - Model Context Protocol

## First-Time Setup

After installation, you'll need to initialize ctxd in each project you want to index:

```bash
cd /path/to/your/project
ctxd init
```

This creates a `.ctxd/` directory with:
- `config.toml` - Configuration file
- `data.lance/` - Vector database directory

See the [Quick Start Guide](quickstart.md) for next steps.

## Troubleshooting

### ImportError: No module named 'ctxd'

**Solution**: Make sure you've activated your virtual environment:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### torch installation fails

**Solution**: If PyTorch installation fails, try installing it separately first:
```bash
# CPU-only version (smaller, faster to install)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Then install ctxd
pip install -e .
```

### tree-sitter compilation errors

**Solution**: Some systems require a C compiler for tree-sitter. Install build tools:

**Ubuntu/Debian**:
```bash
sudo apt-get install build-essential
```

**macOS**:
```bash
xcode-select --install
```

**Windows**:
Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)

### Memory issues during indexing

**Solution**: If you encounter memory issues with large codebases:
1. Reduce batch size in `.ctxd/config.toml`:
   ```toml
   [embeddings]
   batch_size = 16  # Default is 32
   ```
2. Consider excluding large directories (node_modules, etc.)

### Permission errors

**Solution**: Ensure you have write permissions in the project directory:
```bash
chmod -R u+w /path/to/project/.ctxd
```

## Uninstallation

To uninstall ctxd:

```bash
# Using pip
pip uninstall ctxd

# Also remove project-specific data
rm -rf .ctxd/  # Run this in each indexed project
```

## Next Steps

Once installed, proceed to the [Quick Start Guide](quickstart.md) to learn how to use ctxd.
