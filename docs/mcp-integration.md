# MCP Integration Guide

This guide explains how to integrate ctxd with Claude Code using the Model Context Protocol (MCP).

## What is MCP?

The Model Context Protocol (MCP) is a standard for connecting AI assistants to external tools and data sources. ctxd implements an MCP server that exposes semantic code search capabilities to Claude Code.

## Benefits of MCP Integration

- **Semantic Code Search**: Claude can search your codebase by meaning, not just keywords
- **Token Reduction**: ~40% fewer tokens by retrieving only relevant code
- **Better Context**: Claude gets precise code snippets instead of entire files
- **Always Current**: Searches the latest indexed version of your code
- **Privacy**: All data stays local - no code sent to external services

## Prerequisites

1. **Claude Code installed** (version with MCP support)
2. **ctxd installed** in your Python environment
3. **Project indexed** with ctxd

If you haven't installed ctxd yet, see the [Installation Guide](installation.md).

## Setup Steps

### Step 1: Initialize ctxd in Your Project

```bash
cd /path/to/your/project
ctxd init
ctxd index
```

This creates `.ctxd/` with the vector database.

### Step 2: Configure Claude Code

Add ctxd to Claude Code's MCP settings.

**Location**: `~/.config/claude-code/settings.json`

**Configuration**:
```json
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/absolute/path/to/your/project"]
    }
  }
}
```

**Important**: Replace `/absolute/path/to/your/project` with the full path to your project directory (the one containing `.ctxd/`).

**Example**:
```json
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/home/user/projects/my-app"]
    }
  }
}
```

### Step 3: Restart Claude Code

Restart Claude Code to load the MCP server:

```bash
# Exit Claude Code and restart
claude-code
```

### Step 4: Verify Integration

Ask Claude Code to search your code:

```
Search for "database connection" in the codebase
```

Claude should use the `ctx_search` tool and return relevant results.

## Available MCP Tools

Once configured, Claude Code has access to three tools:

### 1. ctx_search

Search for code semantically across the indexed codebase.

**Parameters**:
- `query` (string, required): Natural language or keyword query
- `limit` (integer, optional): Max results (default: from config, usually 10)
- `file_filter` (string, optional): Glob pattern (e.g., "src/**/*.py")
- `branch` (string, optional): Git branch filter
- `extensions` (list, optional): File extensions (e.g., [".py", ".js"])
- `directories` (list, optional): Directory prefixes (e.g., ["src/", "lib/"])
- `chunk_types` (list, optional): Chunk types (e.g., ["function", "class"])
- `languages` (list, optional): Languages (e.g., ["python", "javascript"])
- `mode` (string, optional): "vector", "fts", or "hybrid" (default: from config)
- `expand_context` (boolean, optional): Include surrounding lines
- `deduplicate` (boolean, optional): Remove overlapping chunks

**Example Claude queries**:
- "Search for authentication logic"
- "Find error handling code in Python files"
- "Search for database queries in the src/ directory"
- "Find all classes related to user management"

### 2. ctx_status

Get statistics about the indexed codebase.

**No parameters required.**

**Returns**:
- Total files and chunks indexed
- Index size
- Languages detected
- Chunk type distribution
- Last indexed timestamp

**Example Claude queries**:
- "Show me the index status"
- "How many files are indexed?"
- "What languages are in this codebase?"

### 3. ctx_index

Trigger indexing or re-indexing of files.

**Parameters**:
- `path` (string, optional): Relative path to index (default: ".")
- `force` (boolean, optional): Force re-index all files (default: false)

**Example Claude queries**:
- "Re-index the src/ directory"
- "Index the entire project"
- "Force re-index everything"

## Usage Examples

### Basic Search

**You**: "Find the user authentication code"

**Claude**: Uses `ctx_search` with query "user authentication", returns relevant functions/classes with file locations and code snippets.

### Filtered Search

**You**: "Search for error handling, but only in Python files in the src/ directory"

**Claude**: Uses `ctx_search` with:
- query: "error handling"
- extensions: [".py"]
- directories: ["src/"]

### Understanding Codebase

**You**: "How is the database connection established?"

**Claude**:
1. Uses `ctx_search` with query "database connection"
2. Analyzes returned code snippets
3. Explains the connection logic

### Locating Similar Code

**You**: "Find all the API endpoints"

**Claude**: Uses `ctx_search` with query "API endpoints" and may filter by chunk_type: ["function"] to find endpoint handlers.

### Checking Index

**You**: "Is the codebase indexed?"

**Claude**: Uses `ctx_status` to show index statistics.

### Updating Index

**You**: "I just added new files. Can you re-index?"

**Claude**: Uses `ctx_index` to trigger incremental re-indexing.

## Advanced Configuration

### Multiple Projects

You can configure ctxd for multiple projects:

```json
{
  "mcpServers": {
    "ctxd-project-a": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/path/to/project-a"]
    },
    "ctxd-project-b": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/path/to/project-b"]
    }
  }
}
```

Claude Code will have separate search tools for each project.

### Custom Configuration

The MCP server reads from `.ctxd/config.toml` in the project. You can customize search behavior:

```toml
[search]
mode = "hybrid"          # Use hybrid search
default_limit = 20       # Return more results
expand_context = true    # Show surrounding lines
context_lines_before = 5
context_lines_after = 5
```

See [Configuration Guide](configuration.md) for all options.

### Logging and Debugging

Enable MCP server logging:

```bash
# Set environment variable before starting Claude Code
export CTXD_LOG_LEVEL=DEBUG

# Then start Claude Code
claude-code
```

Logs will be written to `.ctxd/mcp-server.log`.

## Troubleshooting

### Claude Code doesn't see ctxd tools

**Check**:
1. Verify `ctxd-mcp` is in your PATH:
   ```bash
   which ctxd-mcp
   ```
2. Verify settings.json syntax is valid JSON
3. Verify project-root path is absolute and correct
4. Restart Claude Code completely

### "No chunks found" in search results

**Solutions**:
1. Check index status:
   ```bash
   cd /path/to/project
   ctxd status
   ```
2. Re-index if needed:
   ```bash
   ctxd index
   ```
3. Verify `.ctxd/` directory exists in project

### Slow search performance

**Solutions**:
1. Enable query caching in `.ctxd/config.toml`:
   ```toml
   [search]
   enable_cache = true
   cache_size = 200
   ```
2. Use hybrid or vector mode instead of FTS for semantic queries
3. Consider increasing `min_score` to reduce low-quality results

### MCP server crashes

**Check**:
1. MCP server logs: `.ctxd/mcp-server.log`
2. Python environment is activated
3. All dependencies are installed:
   ```bash
   pip list | grep -E "lancedb|sentence-transformers|mcp"
   ```

### "Permission denied" errors

**Solutions**:
1. Check `.ctxd/` directory permissions:
   ```bash
   chmod -R u+w .ctxd/
   ```
2. Verify your user owns the directory:
   ```bash
   ls -la .ctxd/
   ```

## Best Practices

### 1. Keep Index Updated

Enable file watching during development:
```bash
ctxd watch &
```

Or periodically re-index:
```bash
ctxd index
```

### 2. Use Semantic Queries

Take advantage of semantic search:
- Good: "find authentication logic"
- Less good: "find authenticate"

### 3. Use Filters Effectively

Combine filters for precise results:
- "Search for error handling in Python API files in src/"

Claude will apply appropriate filters automatically.

### 4. Check Index Status Regularly

Periodically ask Claude:
- "Show index status"
- "How many files are indexed?"

### 5. Configure for Your Workflow

Adjust `.ctxd/config.toml` based on your needs:
- More context: `expand_context = true`
- More results: `default_limit = 20`
- Better quality: `min_score = 0.4`

## Performance Tips

### For Large Codebases (10,000+ files)

1. Use parallel indexing (enabled by default)
2. Increase cache size:
   ```toml
   [search]
   cache_size = 200
   ```
3. Consider excluding large directories:
   ```toml
   [indexer]
   exclude_patterns = ["docs/**", "examples/**"]
   ```

### For Faster Searches

1. Use hybrid or vector mode
2. Enable caching
3. Set reasonable `default_limit` (10-20)
4. Use filters to narrow scope

## Privacy and Security

ctxd is **local-first**:
- All code stays on your machine
- No external API calls for indexing or search
- Vector database is stored locally in `.ctxd/`
- MCP communication is local (localhost only)

**Best practices**:
- Don't commit `.ctxd/` to version control (add to `.gitignore`)
- Back up `.ctxd/config.toml` if customized
- Index databases are safe to delete and rebuild

## Next Steps

- [Usage Guide](usage.md) - Manual ctxd commands
- [Configuration Guide](configuration.md) - Customize behavior
- [Architecture Guide](architecture.md) - How it works
