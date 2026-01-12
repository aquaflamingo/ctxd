# Quick Start Guide

This guide will walk you through indexing your first codebase and performing semantic searches.

## Step 1: Initialize ctxd in Your Project

Navigate to your project directory and initialize ctxd:

```bash
cd /path/to/your/project
ctxd init
```

**What this does**:
- Creates a `.ctxd/` directory in your project
- Generates a default `config.toml` configuration file
- Sets up the directory structure for the vector database

**Output**:
```
✓ Initialized ctxd in /path/to/your/project
  Configuration saved to .ctxd/config.toml
  Database will be stored in .ctxd/data.lance/
```

## Step 2: Index Your Codebase

Index all files in the current directory:

```bash
ctxd index
```

**What this does**:
- Scans your project directory (respecting `.gitignore`)
- Detects programming languages
- Extracts semantic chunks (functions, classes, etc.)
- Generates vector embeddings
- Stores everything in the local database

**Example output**:
```
Indexing files... ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00

✓ Indexing complete!
  Files indexed: 234
  Chunks created: 1,842
  Time taken: 45.3s
  Average: 5.2 files/sec
```

**Index specific paths**:
```bash
# Index only the src/ directory
ctxd index src/

# Force re-index all files (ignore incremental optimization)
ctxd index --force

# Index with specific git branch tracking
ctxd index --branch main
```

## Step 3: Search Your Code

Perform semantic searches:

```bash
# Basic semantic search
ctxd search "database connection"

# Search with filters
ctxd search "authentication" --limit 5 --extension .py

# Search in specific directory
ctxd search "error handling" --directory src/
```

**Example output**:
```
Searching for: database connection

──────────────────────────────────────────────────────────
Match 1 (Score: 0.87) - src/db/connection.py:12-28

12  def create_connection_pool(
13      host: str,
14      port: int = 5432,
15      max_connections: int = 10
16  ) -> ConnectionPool:
17      """Create a database connection pool with the specified parameters."""
18      pool = ConnectionPool(
19          host=host,
20          port=port,
21          max_size=max_connections
22      )
23      return pool

Type: function | Language: python | Branch: main
──────────────────────────────────────────────────────────

Found 5 matches in 3 files
```

## Step 4: Check Index Status

View statistics about your indexed codebase:

```bash
ctxd status
```

**Example output**:
```
Index Status
────────────────────────────────────────────
Project: /path/to/your/project
Database: .ctxd/data.lance/

Files Indexed:     234
Chunks Stored:   1,842
Index Size:      12.4 MB
Last Indexed:    2026-01-10 14:32:15

Languages Detected:
  python        156 files
  javascript     42 files
  typescript     28 files
  markdown        8 files
```

## Step 5: Configure for Your Needs (Optional)

Edit `.ctxd/config.toml` to customize behavior:

```bash
# Open in your editor
vim .ctxd/config.toml
```

**Common customizations**:

```toml
[indexer]
# Exclude additional patterns
exclude_patterns = [
    "node_modules/**",
    "*.min.js",
    "dist/**",
    "build/**",
    ".venv/**",
    "vendor/**"  # Add custom exclusions
]

[search]
# Use hybrid search (recommended)
mode = "hybrid"

# Show more results by default
default_limit = 20

# Expand context around matches
expand_context = true
context_lines_before = 5
context_lines_after = 5
```

After changing config, re-index:
```bash
ctxd index --force
```

## Next Steps

### Enable File Watching
Automatically re-index when files change:

```bash
ctxd watch
```

This runs in the background and updates the index as you edit files.

### Integrate with Claude Code
Set up MCP integration to give Claude semantic search capabilities. See the [MCP Integration Guide](mcp-integration.md).

### Clean and Reset
If you need to start fresh:

```bash
# Remove all indexed data
ctxd clean

# Re-initialize and re-index
ctxd init
ctxd index
```

## Common Workflows

### Workflow 1: New Project Setup
```bash
cd my-new-project
ctxd init
ctxd index
ctxd watch &  # Auto-update in background
```

### Workflow 2: Large Project with Selective Indexing
```bash
cd large-project
ctxd init

# Edit .ctxd/config.toml to exclude more directories
vim .ctxd/config.toml

# Index only source directories
ctxd index src/ lib/
```

### Workflow 3: Research Existing Codebase
```bash
cd unfamiliar-codebase
ctxd init
ctxd index

# Search for key concepts
ctxd search "authentication flow"
ctxd search "database schema"
ctxd search "API endpoints"
```

### Workflow 4: Daily Development
```bash
# Morning: start file watcher
ctxd watch &

# Work on code...

# Search as needed
ctxd search "payment processing"

# Evening: check status
ctxd status
```

## Tips for Best Results

1. **Let initial indexing complete**: First-time indexing can take a few minutes for large codebases. Subsequent updates are much faster.

2. **Use semantic queries**: Instead of searching for function names like `getUserById`, search for concepts like "user lookup by ID".

3. **Combine filters**: Use `--extension`, `--directory`, and `--branch` together to narrow results.

4. **Enable hybrid mode**: The default hybrid search mode combines semantic and keyword search for best results.

5. **Expand context when needed**: Use `--expand-context` flag to see more lines around matches.

6. **Keep index updated**: Use `ctxd watch` during development or run `ctxd index` periodically.

7. **Check status regularly**: Use `ctxd status` to ensure your index is up-to-date.

## Troubleshooting

### "No chunks found" after indexing
- Check that files aren't excluded by `.gitignore` or config patterns
- Verify file extensions are supported
- Try `ctxd index --force` to re-index

### Searches returning no results
- Check index status: `ctxd status`
- Try broader queries
- Use `--mode fts` for exact keyword matching
- Verify files containing expected code are indexed

### Slow indexing
- Large codebases take time on first index
- Exclude unnecessary directories in config
- Subsequent indexes are incremental and much faster

### High memory usage
- Reduce batch size in config: `embeddings.batch_size = 16`
- Index in smaller chunks: `ctxd index src/` then `ctxd index lib/`

## Get Help

```bash
# General help
ctxd --help

# Command-specific help
ctxd index --help
ctxd search --help
```

For more detailed information, see:
- [Usage Guide](usage.md) - Comprehensive command reference
- [Configuration Guide](configuration.md) - All configuration options
- [Architecture Guide](architecture.md) - How ctxd works
