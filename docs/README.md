# ctxd Documentation

Welcome to the ctxd documentation! This directory contains comprehensive guides for using and understanding ctxd.

## Documentation Structure

### Getting Started

1. **[Overview](index.md)** - Introduction to ctxd and its features
2. **[Installation](installation.md)** - How to install ctxd
3. **[Quick Start](quickstart.md)** - Get up and running in 5 minutes

### User Guides

4. **[Usage Guide](usage.md)** - Complete CLI command reference
5. **[Configuration](configuration.md)** - All configuration options explained
6. **[Claude Code Guide](claude-code-guide.md)** - Using ctxd with Claude Code (MCP and CLI)
7. **[MCP Integration](mcp-integration.md)** - Detailed MCP setup reference

### Developer Resources

7. **[Architecture](architecture.md)** - How ctxd works under the hood
8. **[API Reference](api.md)** - Python API documentation

## Quick Navigation

### I want to...

**Get started quickly**
→ [Quick Start Guide](quickstart.md)

**Install ctxd**
→ [Installation Guide](installation.md)

**Use ctxd with Claude Code**
→ [Claude Code Guide](claude-code-guide.md) (covers both MCP and non-MCP usage)

**Customize ctxd's behavior**
→ [Configuration Guide](configuration.md)

**Use ctxd from Python**
→ [API Reference](api.md)

**Understand how ctxd works**
→ [Architecture Guide](architecture.md)

**Learn all CLI commands**
→ [Usage Guide](usage.md)

## What is ctxd?

ctxd (pronounced "context-d") is a **local-first semantic code search daemon** designed for AI coding assistants like Claude Code. It indexes your codebase into a local vector database, enabling semantic search without loading entire directories into context.

### Key Features

- **Semantic Search**: Find code by meaning, not just keywords
- **Token Reduction**: ~40% fewer tokens by retrieving only relevant snippets
- **Local-First**: All data stays on your machine
- **Multi-Language**: Supports Python, JavaScript, TypeScript, Go, Markdown, and more
- **MCP Integration**: Native integration with Claude Code
- **Fast**: Parallel processing, batch embeddings, query caching

## Common Tasks

### First-Time Setup

```bash
# Install ctxd
pip install -e .

# Initialize in your project
cd /path/to/project
ctxd init

# Index your codebase
ctxd index
```

See: [Installation](installation.md) | [Quick Start](quickstart.md)

### Searching Code

```bash
# Semantic search
ctxd search "database connection"

# With filters
ctxd search "authentication" --extension .py --directory src/
```

See: [Usage Guide](usage.md)

### Integrating with Claude Code

```bash
# 1. Index your project
ctxd init
ctxd index

# 2. Add to Claude Code settings
# See MCP Integration guide for details
```

See: [MCP Integration](mcp-integration.md)

### Customizing Behavior

Edit `.ctxd/config.toml`:

```toml
[search]
mode = "hybrid"        # Use hybrid search
default_limit = 20     # Return more results

[indexer]
exclude_patterns = [   # Exclude more directories
    "vendor/**",
    "docs/**"
]
```

See: [Configuration Guide](configuration.md)

### Using from Python

```python
from ctxd import Config, VectorStore, EmbeddingModel, Indexer

# Setup
config = Config("/path/to/project")
store = VectorStore(config.db_path)
embeddings = EmbeddingModel()
indexer = Indexer(store, embeddings, config)

# Index
indexer.index_path("/path/to/project")

# Search
results = store.search("database connection", mode="hybrid")
```

See: [API Reference](api.md)

## Documentation Format

All documentation is written in GitHub-flavored Markdown and can be read:
- On GitHub (if hosted in a repository)
- In any Markdown viewer
- In your terminal with a Markdown reader like `glow`
- On a documentation website (e.g., MkDocs, Docusaurus)

## Getting Help

- **Usage Questions**: See [Usage Guide](usage.md)
- **Configuration Issues**: See [Configuration Guide](configuration.md)
- **Troubleshooting**: Check relevant guide for "Troubleshooting" section
- **Bug Reports**: [GitHub Issues](https://github.com/yourusername/ctxd/issues)

## Contributing

We welcome contributions! Areas where you can help:

- **Documentation**: Improve clarity, add examples, fix typos
- **Features**: Add new chunkers, improve search quality
- **Testing**: Add test coverage, report bugs
- **Performance**: Optimize indexing and search

## Project Links

- **Main README**: [/README.md](../README.md)
- **Source Code**: [/ctxd](../ctxd)
- **Tests**: [/tests](../tests)

## Version

This documentation is for ctxd version 0.1.0.

Last updated: 2026-01-10
