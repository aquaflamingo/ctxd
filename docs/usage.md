# Usage Guide

Complete reference for all ctxd commands and options.

## Command Overview

```bash
ctxd [COMMAND] [OPTIONS]
```

Available commands:
- `init` - Initialize ctxd in a project
- `index` - Index files in the project
- `search` - Search indexed code
- `status` - Show index statistics
- `clean` - Remove all indexed data
- `watch` - Watch for file changes and auto-index

## ctxd init

Initialize ctxd in the current project directory.

### Usage

```bash
ctxd init [OPTIONS]
```

### Options

- `--force` - Overwrite existing configuration
- `--help` - Show help message

### Examples

```bash
# Initialize in current directory
ctxd init

# Force re-initialization (overwrites existing config)
ctxd init --force
```

### What It Does

1. Creates `.ctxd/` directory
2. Generates default `config.toml`
3. Sets up database directory structure

### Files Created

- `.ctxd/config.toml` - Configuration file
- `.ctxd/data.lance/` - Database directory (created on first index)

## ctxd index

Index files in the project directory.

### Usage

```bash
ctxd index [PATH] [OPTIONS]
```

### Arguments

- `PATH` - Path to index (default: current directory)

### Options

- `--force` - Force re-index all files, ignoring incremental optimization
- `--branch TEXT` - Git branch name to associate with indexed chunks
- `--parallel / --no-parallel` - Enable/disable parallel processing (default: parallel)
- `--workers INTEGER` - Number of worker threads for parallel processing (default: CPU count)
- `--help` - Show help message

### Examples

```bash
# Index current directory
ctxd index

# Index specific path
ctxd index src/

# Force re-index all files
ctxd index --force

# Index with specific branch
ctxd index --branch develop

# Index with custom parallelization
ctxd index --workers 4

# Index without parallelization (sequential)
ctxd index --no-parallel
```

### Behavior

**Incremental Indexing** (default):
- Only indexes new or modified files
- Uses file hash to detect changes
- Much faster for repeated indexing

**Force Mode** (`--force`):
- Re-indexes all files regardless of changes
- Use when:
  - Config has changed (chunking settings, etc.)
  - Index appears corrupted
  - Upgrading ctxd version with schema changes

**Parallel Processing**:
- Default: Uses all available CPU cores
- Significantly faster for large codebases
- Can be disabled with `--no-parallel` for debugging

### What Gets Indexed

**Included**:
- All text files in the project
- Respects `.gitignore` patterns
- Applies exclude patterns from config

**Excluded** (default):
- `node_modules/**`
- `*.min.js`
- `dist/**`, `build/**`
- `.venv/**`, `venv/**`
- `__pycache__/**`
- `.git/**`
- Binary files
- Files larger than `max_file_size_bytes` (default: 1MB)

### Performance

Typical performance (depends on hardware):
- Small project (100 files): ~5-10 seconds
- Medium project (1,000 files): ~30-60 seconds
- Large project (10,000 files): ~5-10 minutes

Incremental re-indexing: usually under 5 seconds unless many files changed.

## ctxd search

Search indexed code semantically or by keywords.

### Usage

```bash
ctxd search QUERY [OPTIONS]
```

### Arguments

- `QUERY` - Search query (natural language or keywords)

### Options

**Result Options**:
- `--limit INTEGER` - Maximum number of results (default: from config, usually 10)
- `--mode [vector|fts|hybrid]` - Search mode (default: from config, usually hybrid)
- `--expand-context / --no-expand-context` - Include surrounding lines (default: from config)
- `--deduplicate / --no-deduplicate` - Remove overlapping chunks (default: from config)

**Filter Options**:
- `--extension TEXT` - Filter by file extension (e.g., `.py`, `.js`), can be repeated
- `--directory TEXT` - Filter by directory prefix (e.g., `src/`), can be repeated
- `--file-filter TEXT` - Filter by glob pattern (e.g., `src/**/*.py`)
- `--branch TEXT` - Filter by git branch
- `--chunk-type TEXT` - Filter by chunk type (e.g., `function`, `class`), can be repeated
- `--language TEXT` - Filter by language (e.g., `python`, `javascript`), can be repeated

**Display Options**:
- `--help` - Show help message

### Examples

```bash
# Basic semantic search
ctxd search "database connection"

# Limit results
ctxd search "authentication" --limit 5

# Filter by file extension
ctxd search "error handling" --extension .py

# Filter by directory
ctxd search "API endpoints" --directory src/api/

# Multiple filters
ctxd search "user validation" --extension .py --extension .js --directory src/

# Use glob pattern
ctxd search "config loading" --file-filter "src/**/*.py"

# Filter by chunk type
ctxd search "initialization" --chunk-type function

# Filter by language
ctxd search "async operations" --language python

# Use keyword search only
ctxd search "authenticate_user" --mode fts

# Use vector search only
ctxd search "how to handle errors" --mode vector

# Expand context around matches
ctxd search "payment processing" --expand-context

# Disable deduplication
ctxd search "logging" --no-deduplicate
```

### Search Modes

**Vector Mode** (`--mode vector`):
- Pure semantic search using embeddings
- Best for conceptual queries
- Example: "how to connect to database"

**FTS Mode** (`--mode fts`):
- Full-text keyword search using BM25
- Best for exact terms and identifiers
- Example: "authenticate_user"

**Hybrid Mode** (`--mode hybrid`, default):
- Combines vector and FTS using Reciprocal Rank Fusion
- Best of both worlds
- Recommended for most searches

### Output Format

```
Searching for: database connection

──────────────────────────────────────────────────────────
Match 1 (Score: 0.87) - src/db/connection.py:12-28

[Code snippet with syntax highlighting]

Type: function | Language: python | Branch: main
──────────────────────────────────────────────────────────

Found 5 matches in 3 files
```

## ctxd status

Display index statistics and information.

### Usage

```bash
ctxd status [OPTIONS]
```

### Options

- `--help` - Show help message

### Example

```bash
ctxd status
```

### Output

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

Chunk Types:
  function      892 chunks
  class         234 chunks
  method        456 chunks
  paragraph     260 chunks
```

## ctxd clean

Remove all indexed data from the project.

### Usage

```bash
ctxd clean [OPTIONS]
```

### Options

- `--force` - Skip confirmation prompt
- `--help` - Show help message

### Examples

```bash
# Clean with confirmation
ctxd clean

# Clean without confirmation
ctxd clean --force
```

### What It Does

1. Deletes all data in `.ctxd/data.lance/`
2. Removes the vector database
3. Preserves configuration file

### When to Use

- Starting fresh with new indexing strategy
- Fixing corrupted index
- Freeing disk space
- Testing different configurations

After cleaning, run `ctxd index` to rebuild the index.

## ctxd watch

Watch for file changes and automatically re-index.

### Usage

```bash
ctxd watch [OPTIONS]
```

### Options

- `--debounce FLOAT` - Seconds to wait before re-indexing after changes (default: 2.0)
- `--help` - Show help message

### Examples

```bash
# Start watching with default settings
ctxd watch

# Watch with custom debounce
ctxd watch --debounce 5.0

# Run in background (Unix)
ctxd watch &

# Run in background with nohup
nohup ctxd watch > /dev/null 2>&1 &
```

### Behavior

- Monitors all files in the project directory
- Respects `.gitignore` patterns
- Debounces rapid changes (waits for quiet period)
- Triggers incremental re-indexing
- Runs until interrupted (Ctrl+C)

### When to Use

- During active development
- When you want always-current search results
- In long-running development sessions

### Performance Impact

- Minimal CPU usage when idle
- Brief spike during re-indexing
- Incremental indexing is fast (usually <5 seconds)

## Global Options

These options work with any command:

- `--help` - Show help and exit
- `--version` - Show version and exit

### Examples

```bash
# Show general help
ctxd --help

# Show version
ctxd --version

# Show command-specific help
ctxd index --help
ctxd search --help
```

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Command-line usage error

## Environment Variables

Currently, ctxd does not use environment variables. All configuration is in `.ctxd/config.toml`.

## Configuration Files

See [Configuration Guide](configuration.md) for details on `.ctxd/config.toml`.

## Next Steps

- [Configuration Guide](configuration.md) - Customize ctxd behavior
- [MCP Integration](mcp-integration.md) - Connect to Claude Code
- [Architecture Guide](architecture.md) - Understand how ctxd works
