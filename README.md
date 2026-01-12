# ctxd

**Local-first semantic code search daemon for AI coding assistants**

`ctxd` is a semantic code search tool that indexes your codebase into a local vector database, enabling AI assistants like Claude Code to query relevant code snippets without loading entire directory structures into context. This dramatically reduces token usage (target: ~40% reduction) while improving code understanding.

## Features

- **Hybrid Search:** Combines semantic (vector) and keyword (BM25) search for best results
- **Rich Filtering:** Filter by file extension, directory, chunk type, language, and branch
- **Result Enhancement:** De-duplication, context expansion, and recency ranking
- **Local-First:** All data stays on your machine - no cloud dependencies
- **Incremental Indexing:** Only re-indexes changed files for fast updates
- **Multi-Language Support:** AST-based chunking for Python, JavaScript, TypeScript, Go, and Markdown
- **MCP Integration:** Native integration with Claude Code via Model Context Protocol
- **File System Watching:** Automatic re-indexing when files change
- **CLI Interface:** Full-featured command-line interface for manual usage

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd ctxd

# Install with uv
uv pip install -e .

# Or install from source
pip install -e .
```

To install development dependencies:

```bash
uv pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize ctxd in your project

```bash
cd /path/to/your/project
ctxd init
```

This creates a `.ctxd/` directory with configuration and vector database.

### 2. Index your codebase

```bash
# Index current directory
ctxd index

# Index specific path
ctxd index src/

# Force re-index all files
ctxd index --force
```

### 3. Search your code

```bash
# Semantic search
ctxd search "authentication function"

# Get index statistics
ctxd status
```

## MCP Integration with Claude Code

`ctxd` integrates with Claude Code through the Model Context Protocol (MCP), allowing Claude to search your indexed codebase directly.

### Setup

1. **Initialize ctxd in your project** (if you haven't already):

```bash
cd /path/to/your/project
ctxd init
ctxd index  # Index your codebase
```

2. **Configure Claude Code to use ctxd**:

Add the following to your Claude Code MCP settings (`~/.config/claude-code/settings.json`):

```json
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/path/to/your/project"]
    }
  }
}
```

Replace `/path/to/your/project` with the absolute path to your project directory.

3. **Restart Claude Code** to load the MCP server.

### Available Tools

Once configured, Claude Code will have access to these tools:

#### `ctx_search`
Search for code semantically across your indexed codebase with advanced filtering and hybrid search.

**Parameters:**
- `query` (string, required): Natural language search query
- `limit` (int, optional): Maximum results to return (default: 10)
- `file_filter` (string, optional): Glob pattern to filter files (e.g., "*.py", "src/**")
- `branch` (string, optional): Filter by git branch (e.g., "main", "develop")
- `extensions` (list[string], optional): Filter by file extensions (e.g., [".py", ".js"])
- `directories` (list[string], optional): Filter by directory prefixes (e.g., ["src/", "lib/"])
- `chunk_types` (list[string], optional): Filter by chunk type (e.g., ["function", "class"])
- `languages` (list[string], optional): Filter by programming language (e.g., ["python", "javascript"])
- `mode` (string, optional): Search mode - "vector", "fts", or "hybrid" (default: from config)
- `expand_context` (bool, optional): Include surrounding lines from source files (default: from config)
- `deduplicate` (bool, optional): Remove overlapping chunks (default: from config)

**Example usage by Claude:**
```
Search for "database connection pooling" in your codebase

Search for "authentication" only in Python functions in the src/ directory

Search for "error handling" using hybrid search mode
```

#### `ctx_status`
Get statistics about the indexed codebase.

**Returns:**
- Total files and chunks indexed
- Index size
- Languages detected
- Last indexed timestamp

**Example usage by Claude:**
```
Show me the status of the code index
```

#### `ctx_index`
Trigger indexing of files in the project.

**Parameters:**
- `path` (string, optional): Path to index relative to project root (default: ".")
- `force` (bool, optional): Force re-indexing of unchanged files (default: false)

**Example usage by Claude:**
```
Re-index the src/ directory
```

### Usage Tips

- **Index regularly**: Run `ctxd index` after significant code changes
- **Watch mode**: Use `ctxd watch` to automatically re-index on file changes
- **File filters**: Use glob patterns in `ctx_search` to narrow results to specific files
- **Token savings**: Claude can search thousands of files without loading them into context

## Claude Code Skill

The `skills/` directory contains a comprehensive skill template that teaches Claude Code agents how to effectively use ctxd. This skill provides instructions on when to use ctxd, how to formulate queries, search strategies, and common workflows.

### Quick Install

```bash
# Install the skill in your project
cd /path/to/ctxd
./skills/install-skill.sh /path/to/your/project
```

This copies the skill instructions to `.claude/instructions/` in your project, where Claude Code will automatically load them.

### What the Skill Teaches Claude

- When to use ctxd vs other tools (Grep, Glob, Read)
- How to formulate effective semantic queries
- Search strategies and progressive refinement
- Workflow patterns for common scenarios (debugging, exploration, etc.)
- Best practices for combining ctxd with other tools
- Error handling and troubleshooting

### With vs Without the Skill

**Without skill:** Claude uses keyword search (Grep) and reads entire files, consuming many tokens.

**With skill:** Claude uses semantic search to find relevant code chunks, provides ranked results with context, and efficiently navigates large codebases.

See [`skills/EXAMPLES.md`](skills/EXAMPLES.md) for detailed before/after comparisons.

### Learn More

- [Skill README](skills/README.md) - Installation and usage guide
- [Skill Template](skills/ctxd-search.md) - The actual skill instructions
- [Examples](skills/EXAMPLES.md) - Before/after comparisons

## Configuration

Configuration is stored in `.ctxd/config.toml`. You can customize:

### Indexer Settings
```toml
[indexer]
exclude_patterns = [
    "node_modules/**",
    "*.min.js",
    "dist/**",
    "build/**",
    ".venv/**",
    "__pycache__/**"
]
max_file_size_bytes = 1048576  # 1MB
max_chunk_size = 500
chunk_overlap = 50
```

### Embeddings Settings
```toml
[embeddings]
model = "all-MiniLM-L6-v2"  # sentence-transformers model
batch_size = 32
```

### Search Settings
```toml
[search]
default_limit = 10
min_score = 0.3  # Minimum similarity score (0-1)

# Hybrid search (Phase 4)
mode = "hybrid"           # "vector", "fts", or "hybrid"
fts_weight = 0.5          # BM25 weight for hybrid mode (0.0-1.0)

# Result enhancement (Phase 4)
deduplicate = true        # Remove overlapping chunks from same file
overlap_threshold = 0.5   # Overlap percentage threshold (0.0-1.0)
expand_context = false    # Include surrounding lines from source files
context_lines_before = 3  # Lines to include before chunk
context_lines_after = 3   # Lines to include after chunk
recency_weight = 0.1      # Recency boost for tie-breaking (0.0-1.0)
```

### Search Modes Explained

**Vector Mode** (`mode = "vector"`):
- Pure semantic search using embedding similarity
- Best for conceptual queries like "error handling" or "database connection"
- May miss exact keyword matches

**FTS Mode** (`mode = "fts"`):
- Full-text keyword search using BM25 ranking
- Best for exact terms like "authenticate_user" or specific identifiers
- May miss semantically similar but differently worded code

**Hybrid Mode** (`mode = "hybrid"`, recommended):
- Combines vector and FTS search using Reciprocal Rank Fusion (RRF)
- Best of both worlds: finds semantically similar code AND exact keyword matches
- Recommended for most use cases

## Supported Languages

- **AST-based chunking:** Python
- **Paragraph-based chunking:** JavaScript, TypeScript, Go, Rust, Java, C, C++, Markdown, JSON, YAML, TOML, and more

New language support can be added by implementing custom chunking strategies.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ctxd --cov-report=html

# Run specific test file
pytest tests/test_mcp.py
```

### Project Structure

```
ctxd/
├── ctxd/                    # Main package
│   ├── cli.py               # Command-line interface
│   ├── mcp_server.py        # MCP server implementation
│   ├── indexer.py           # File indexing logic
│   ├── store.py             # Vector store abstraction
│   ├── embeddings.py        # Embedding model wrapper
│   ├── models.py            # Data models
│   ├── config.py            # Configuration management
│   ├── watcher.py           # File system watcher
│   └── chunkers/            # Chunking strategies
├── tests/                   # Test suite
└── .ctxd/                   # Runtime data (created by init)
    ├── config.toml          # Project configuration
    └── data.lance           # LanceDB vector database
```

## How It Works

1. **File Discovery**: Scans project directory respecting `.gitignore`
2. **Language Detection**: Identifies programming language from file extension
3. **Chunking**: Splits files into semantic chunks (functions, classes, paragraphs)
4. **Embedding Generation**: Converts chunks to 384-dim vectors using sentence-transformers
5. **Vector Storage**: Stores chunks with embeddings in LanceDB
6. **Semantic Search**: Finds similar chunks using vector similarity
7. **MCP Integration**: Exposes search tools to Claude Code

## License

[License information to be added]

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
