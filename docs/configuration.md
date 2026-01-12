# Configuration Guide

Complete reference for ctxd configuration options.

## Configuration File

Configuration is stored in `.ctxd/config.toml` in TOML format. This file is created when you run `ctxd init`.

## Full Configuration Example

```toml
[indexer]
# Patterns to exclude from indexing (glob patterns)
exclude_patterns = [
    "node_modules/**",
    "*.min.js",
    "dist/**",
    "build/**",
    ".venv/**",
    "venv/**",
    "__pycache__/**",
    "*.pyc",
    ".git/**",
    ".ctxd/**",
    "vendor/**",
    "target/**"
]

# Maximum file size to index (in bytes)
max_file_size_bytes = 1048576  # 1MB

# Maximum characters per chunk
max_chunk_size = 500

# Overlap between chunks (for paragraph-based chunking)
chunk_overlap = 50

# Parallel processing settings
parallel = true          # Enable parallel file processing
max_workers = null       # null = auto-detect CPU count, or set specific number

[embeddings]
# Sentence-transformers model to use
model = "all-MiniLM-L6-v2"

# Batch size for embedding generation
batch_size = 32

# Device to use: "cuda", "cpu", or "auto"
device = "auto"

[search]
# Default number of results to return
default_limit = 10

# Minimum similarity score (0.0-1.0)
min_score = 0.3

# Search mode: "vector", "fts", or "hybrid"
mode = "hybrid"

# Weight for FTS in hybrid mode (0.0-1.0)
fts_weight = 0.5

# Result enhancement options
deduplicate = true            # Remove overlapping chunks from same file
overlap_threshold = 0.5       # Overlap percentage to consider duplicates
expand_context = false        # Include surrounding lines from source
context_lines_before = 3      # Lines before chunk when expanding
context_lines_after = 3       # Lines after chunk when expanding
recency_weight = 0.1          # Boost for recent chunks in tie-breaking

# Query caching
enable_cache = true           # Enable LRU query cache
cache_size = 100              # Maximum cached queries

[git]
# Enable git integration
enabled = true

# Respect .gitignore files
respect_gitignore = true

[watcher]
# Debounce time in seconds (wait after last change before re-indexing)
debounce_seconds = 2.0

# Patterns to ignore in file watcher (in addition to indexer exclude_patterns)
ignore_patterns = [
    "*.swp",
    "*.tmp",
    "*~",
    ".DS_Store"
]
```

## Configuration Sections

### [indexer]

Controls file indexing behavior.

#### exclude_patterns

**Type**: List of strings
**Default**: See example above

Glob patterns for files and directories to exclude from indexing. Patterns follow standard glob syntax:
- `*` - Matches any characters except `/`
- `**` - Matches any characters including `/`
- `?` - Matches single character
- `[abc]` - Matches any character in brackets

**Examples**:
```toml
exclude_patterns = [
    "test/**",           # Exclude entire test directory
    "*.test.js",         # Exclude test files
    "**/*.min.js",       # Exclude minified JS anywhere
    "docs/**/*.md",      # Exclude markdown in docs
]
```

#### max_file_size_bytes

**Type**: Integer
**Default**: 1048576 (1MB)

Maximum file size to index. Files larger than this are skipped.

**Common values**:
```toml
max_file_size_bytes = 524288     # 512KB - for smaller projects
max_file_size_bytes = 1048576    # 1MB - default
max_file_size_bytes = 5242880    # 5MB - for projects with large files
```

#### max_chunk_size

**Type**: Integer
**Default**: 500

Maximum number of characters per chunk. Affects paragraph-based chunking (fallback chunker). AST-based chunking (Python, JS, TS, Go) uses natural code boundaries and may exceed this slightly.

**Guidelines**:
- Smaller (200-300): More precise results, more chunks, larger database
- Medium (400-600): Balanced (recommended)
- Larger (800-1000): More context per result, fewer chunks

#### chunk_overlap

**Type**: Integer
**Default**: 50

Number of overlapping characters between consecutive chunks in paragraph-based chunking. Helps maintain context across chunk boundaries.

**Guidelines**:
- 0: No overlap (may lose context)
- 50-100: Light overlap (recommended)
- 150-200: Heavy overlap (more context, more storage)

#### parallel

**Type**: Boolean
**Default**: true

Enable parallel file processing during indexing.

```toml
parallel = true   # Use multiple threads (faster)
parallel = false  # Sequential processing (useful for debugging)
```

#### max_workers

**Type**: Integer or null
**Default**: null (auto-detect)

Number of worker threads for parallel processing. Only used if `parallel = true`.

```toml
max_workers = null  # Auto-detect based on CPU count
max_workers = 4     # Use exactly 4 workers
max_workers = 8     # Use 8 workers on multi-core systems
```

### [embeddings]

Controls embedding model configuration.

#### model

**Type**: String
**Default**: "all-MiniLM-L6-v2"

Sentence-transformers model name. The model is downloaded automatically on first use.

**Popular options**:
```toml
# Fast and small (default, 384 dimensions)
model = "all-MiniLM-L6-v2"

# Better quality, larger (768 dimensions)
model = "all-mpnet-base-v2"

# Multilingual support
model = "paraphrase-multilingual-MiniLM-L12-v2"

# Code-specific (if available)
model = "microsoft/codebert-base"
```

**Considerations**:
- Larger models: Better quality, slower, more memory
- Smaller models: Faster, less memory, good enough for most use cases
- Changing models requires re-indexing: `ctxd index --force`

#### batch_size

**Type**: Integer
**Default**: 32

Number of chunks to embed in a single batch. Larger batches are more efficient but use more memory.

```toml
batch_size = 16   # Low memory systems
batch_size = 32   # Default (balanced)
batch_size = 64   # High memory systems, faster indexing
```

#### device

**Type**: String
**Default**: "auto"

Device to use for embedding generation.

```toml
device = "auto"  # Auto-detect (use GPU if available)
device = "cuda"  # Force GPU (requires CUDA)
device = "cpu"   # Force CPU
```

### [search]

Controls search behavior and result formatting.

#### default_limit

**Type**: Integer
**Default**: 10

Default number of search results to return.

#### min_score

**Type**: Float (0.0-1.0)
**Default**: 0.3

Minimum similarity score for results. Lower scores include more results but may be less relevant.

```toml
min_score = 0.2   # More results, lower quality
min_score = 0.3   # Balanced (default)
min_score = 0.5   # Fewer results, higher quality
```

#### mode

**Type**: String ("vector", "fts", "hybrid")
**Default**: "hybrid"

Default search mode.

```toml
mode = "vector"  # Pure semantic search
mode = "fts"     # Pure keyword search (BM25)
mode = "hybrid"  # Combined (recommended)
```

See [Search Modes](#search-modes) for details.

#### fts_weight

**Type**: Float (0.0-1.0)
**Default**: 0.5

Weight for full-text search in hybrid mode. Higher values favor keyword matching.

```toml
fts_weight = 0.3  # Favor semantic search
fts_weight = 0.5  # Balanced (default)
fts_weight = 0.7  # Favor keyword search
```

#### deduplicate

**Type**: Boolean
**Default**: true

Remove overlapping chunks from the same file in search results.

```toml
deduplicate = true   # Remove duplicates (recommended)
deduplicate = false  # Keep all matches
```

#### overlap_threshold

**Type**: Float (0.0-1.0)
**Default**: 0.5

Percentage overlap required to consider chunks duplicates (when `deduplicate = true`).

```toml
overlap_threshold = 0.3  # Aggressive deduplication
overlap_threshold = 0.5  # Balanced (default)
overlap_threshold = 0.8  # Conservative deduplication
```

#### expand_context

**Type**: Boolean
**Default**: false

Include surrounding lines from source files in search results.

```toml
expand_context = false  # Show only the chunk (default)
expand_context = true   # Show chunk with surrounding context
```

#### context_lines_before / context_lines_after

**Type**: Integer
**Default**: 3

Number of lines to include before/after chunks when `expand_context = true`.

```toml
context_lines_before = 5
context_lines_after = 5
```

#### recency_weight

**Type**: Float (0.0-1.0)
**Default**: 0.1

Boost factor for recently modified files in tie-breaking. Higher values favor newer code.

```toml
recency_weight = 0.0   # Ignore recency
recency_weight = 0.1   # Slight favor for recent (default)
recency_weight = 0.3   # Strong favor for recent
```

#### enable_cache

**Type**: Boolean
**Default**: true

Enable LRU cache for search queries.

```toml
enable_cache = true   # Cache queries (faster repeated searches)
enable_cache = false  # No caching
```

#### cache_size

**Type**: Integer
**Default**: 100

Maximum number of queries to cache (when `enable_cache = true`).

### [git]

Controls git integration features.

#### enabled

**Type**: Boolean
**Default**: true

Enable git integration (branch detection, etc.).

#### respect_gitignore

**Type**: Boolean
**Default**: true

Respect `.gitignore` files when indexing.

```toml
respect_gitignore = true   # Skip gitignored files (recommended)
respect_gitignore = false  # Index all files
```

### [watcher]

Controls file watching behavior (for `ctxd watch`).

#### debounce_seconds

**Type**: Float
**Default**: 2.0

Seconds to wait after last file change before triggering re-index.

```toml
debounce_seconds = 1.0   # Quick response
debounce_seconds = 2.0   # Balanced (default)
debounce_seconds = 5.0   # Wait for quiet period
```

#### ignore_patterns

**Type**: List of strings
**Default**: See example

Additional patterns to ignore in file watcher (beyond `indexer.exclude_patterns`).

## Search Modes

### Vector Mode

Pure semantic search using embedding similarity.

**Best for**:
- Conceptual queries: "database connection", "error handling"
- Natural language: "how to authenticate users"
- Finding similar functionality

**Limitations**:
- May miss exact keyword matches
- Requires good embedding model

**Configuration**:
```toml
[search]
mode = "vector"
```

### FTS Mode

Full-text keyword search using BM25 ranking.

**Best for**:
- Exact terms: function names, variable names
- Keywords: "authenticate_user", "DatabasePool"
- Precise matching

**Limitations**:
- Doesn't understand semantics
- May miss similar but differently named code

**Configuration**:
```toml
[search]
mode = "fts"
```

### Hybrid Mode (Recommended)

Combines vector and FTS using Reciprocal Rank Fusion.

**Best for**:
- Most use cases (recommended default)
- Balanced semantic and keyword matching
- Robust across query types

**Configuration**:
```toml
[search]
mode = "hybrid"
fts_weight = 0.5  # Adjust balance
```

## Performance Tuning

### For Large Codebases (10,000+ files)

```toml
[indexer]
parallel = true
max_workers = 8  # Use more cores
max_file_size_bytes = 524288  # Exclude very large files

[embeddings]
batch_size = 64  # Larger batches (if you have RAM)

[search]
enable_cache = true
cache_size = 200  # Cache more queries
```

### For Low-Memory Systems

```toml
[indexer]
parallel = true
max_workers = 2  # Fewer workers

[embeddings]
batch_size = 16  # Smaller batches
model = "all-MiniLM-L6-v2"  # Smaller model

[search]
cache_size = 50  # Smaller cache
```

### For Maximum Quality

```toml
[embeddings]
model = "all-mpnet-base-v2"  # Better model

[search]
mode = "hybrid"
fts_weight = 0.5
expand_context = true
context_lines_before = 5
context_lines_after = 5
deduplicate = true
min_score = 0.4  # Higher threshold
```

### For Maximum Speed

```toml
[embeddings]
model = "all-MiniLM-L6-v2"  # Fast model
batch_size = 64

[search]
mode = "vector"  # Skip FTS
expand_context = false
deduplicate = false
enable_cache = true
```

## Applying Configuration Changes

Most configuration changes require re-indexing:

```bash
# After editing .ctxd/config.toml
ctxd index --force
```

**Search settings** take effect immediately (no re-indexing needed):
- `default_limit`
- `min_score`
- `mode`
- `fts_weight`
- `expand_context`
- `context_lines_before/after`
- `recency_weight`
- `enable_cache`
- `cache_size`

**Requires re-indexing**:
- All `[indexer]` settings
- All `[embeddings]` settings

## Next Steps

- [Usage Guide](usage.md) - Learn ctxd commands
- [Architecture Guide](architecture.md) - Understand internals
- [MCP Integration](mcp-integration.md) - Connect to Claude Code
