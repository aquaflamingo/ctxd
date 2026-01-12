# Architecture Guide

Deep dive into how ctxd works under the hood.

## Overview

ctxd is a semantic code search daemon that combines vector embeddings, full-text search, and AST-based code understanding to provide intelligent code retrieval for AI coding assistants.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│  ┌──────────────┐              ┌────────────────────────┐   │
│  │  CLI (Click) │              │  MCP Server (Claude)   │   │
│  └──────┬───────┘              └───────────┬────────────┘   │
│         │                                  │                │
└─────────┼──────────────────────────────────┼────────────────┘
          │                                  │
          └──────────────┬───────────────────┘
                         │
          ┌──────────────▼───────────────┐
          │       Core Components        │
          │  ┌────────────────────────┐  │
          │  │   Indexer              │  │
          │  │  - File Discovery      │  │
          │  │  - Chunking            │  │
          │  │  - Embedding Gen       │  │
          │  └──────┬─────────────────┘  │
          │         │                    │
          │  ┌──────▼─────────────────┐  │
          │  │   Vector Store         │  │
          │  │  - LanceDB             │  │
          │  │  - Hybrid Search       │  │
          │  │  - Result Enhancement  │  │
          │  └────────────────────────┘  │
          └────────────────────────────┘
                         │
          ┌──────────────▼───────────────┐
          │      Storage Layer           │
          │  ┌────────────────────────┐  │
          │  │  LanceDB (Vectors)     │  │
          │  │  - Vector Index        │  │
          │  │  - FTS Index           │  │
          │  │  - Metadata            │  │
          │  └────────────────────────┘  │
          └──────────────────────────────┘
```

## Core Components

### 1. Indexer (`ctxd/indexer.py`)

The indexer orchestrates the entire indexing pipeline.

**Responsibilities**:
- File discovery and filtering
- Language detection
- Chunker selection
- Parallel processing coordination
- Incremental update management
- Cleanup of stale data

**Indexing Pipeline**:

```
Files → Filter → Detect Lang → Parse/Chunk → Generate Embeddings → Store
  ↓       ↓          ↓             ↓               ↓                ↓
.py    .gitignore  Python    TreeSitter    sentence-transformers  LanceDB
.js    config      JS        Chunker       Batch processing      Vectors
.ts    patterns    TS        Functions     384-dim vectors       + Metadata
```

**Key Features**:

1. **Incremental Indexing**:
   - Computes file hash (SHA-256)
   - Compares with stored hash
   - Only re-indexes if content changed
   - Dramatically faster on subsequent runs

2. **Parallel Processing**:
   - Uses ThreadPoolExecutor
   - Configurable worker count
   - Thread-safe batch accumulation
   - Progress reporting across threads

3. **Batch Embedding**:
   - Accumulates chunks across files
   - Generates embeddings in batches
   - Reduces model loading overhead
   - Configurable batch size

**Code Flow**:
```python
def index_path(path: str, force: bool = False):
    # 1. Discover files
    files = discover_files(path)

    # 2. Process files (parallel or sequential)
    if parallel:
        with ThreadPoolExecutor(max_workers=N) as executor:
            futures = [executor.submit(process_file, f) for f in files]
            # Accumulate chunks across threads
    else:
        chunks = [process_file(f) for f in files]

    # 3. Generate embeddings in batches
    embeddings = embedding_model.embed_batch(chunks)

    # 4. Store in database
    store.add_chunks(chunks, embeddings)

    # 5. Cleanup deleted files
    store.cleanup_deleted_files(current_files)
```

### 2. Chunkers (`ctxd/chunkers/`)

Chunkers split files into semantic units for indexing.

#### Base Chunker (`base.py`)

Abstract base class defining the chunking interface:

```python
class BaseChunker(ABC):
    @abstractmethod
    def chunk_file(self, file_path: str, content: str) -> List[Chunk]:
        """Split file into semantic chunks."""
        pass
```

#### TreeSitter Chunker (`treesitter.py`)

AST-based chunking for Python, JavaScript, TypeScript, and Go.

**How It Works**:

1. **Parse**: Use tree-sitter to parse file into AST
2. **Traverse**: Walk AST to find relevant nodes
3. **Extract**: Extract node text with context (decorators, docstrings)
4. **Create Chunks**: Create chunk objects with metadata

**Node Types Extracted**:
- **Python**: `function_definition`, `class_definition`
- **JavaScript/TypeScript**: `function_declaration`, `class_declaration`, `method_definition`
- **Go**: `function_declaration`, `method_declaration`

**Special Handling**:
- Includes decorators (Python `@decorator`)
- Includes docstrings
- Small files (<50 lines) kept as single chunk
- Preserves indentation and structure

**Example**:
```python
# Input file
@cache
def get_user(user_id: int) -> User:
    """Fetch user by ID."""
    return db.query(User).get(user_id)

# Extracted chunk
{
    "content": "@cache\ndef get_user(user_id: int) -> User:\n    ...",
    "chunk_type": "function",
    "start_line": 1,
    "end_line": 4,
    "metadata": {
        "name": "get_user",
        "has_decorator": true,
        "has_docstring": true
    }
}
```

#### Markdown Chunker (`markdown.py`)

Header-based chunking for Markdown files.

**Strategy**:
- Split on headers (# Header)
- Each section is a chunk
- Preserves header hierarchy
- Includes code blocks within sections

#### Fallback Chunker (`fallback.py`)

Paragraph-based chunking for unsupported languages.

**Strategy**:
- Split on blank lines (paragraphs)
- Configurable max chunk size
- Configurable overlap between chunks
- Merges small paragraphs
- Splits large paragraphs

**Used for**: JSON, YAML, TOML, plain text, etc.

### 3. Embedding Model (`ctxd/embeddings.py`)

Wrapper around sentence-transformers for generating vector embeddings.

**Key Features**:

1. **Lazy Loading**: Model loaded on first use
2. **Device Auto-Detection**: Automatically uses GPU if available
3. **Batch Processing**: Efficient batch embedding generation
4. **Retry Logic**: Handles transient failures

**Model Details**:
- **Default**: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Type**: Sentence transformer
- **Performance**: ~1000 chunks/second on CPU

**Code Flow**:
```python
class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model = None  # Lazy loading

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        if self._model is None:
            self._load_model()

        # Generate embeddings with retry
        embeddings = retry(
            lambda: self._model.encode(texts, batch_size=32)
        )
        return embeddings
```

### 4. Vector Store (`ctxd/store.py`)

Abstraction over LanceDB for vector storage and retrieval.

**Responsibilities**:
- Store chunks with embeddings
- Vector similarity search
- Full-text search (BM25)
- Hybrid search (RRF)
- Result filtering
- Query caching

**Schema**:
```python
{
    "id": "unique_chunk_id",
    "content": "chunk text content",
    "embedding": [0.1, 0.2, ...],  # 384-dim vector
    "file_path": "src/module.py",
    "start_line": 10,
    "end_line": 25,
    "chunk_type": "function",
    "language": "python",
    "branch": "main",
    "file_hash": "sha256...",
    "indexed_at": "2026-01-10T14:32:15",
    "metadata": {...}
}
```

**Search Modes**:

1. **Vector Search**:
   ```python
   # Compute query embedding
   query_vec = embedding_model.embed(query)

   # KNN search in vector space
   results = table.search(query_vec).limit(k).to_list()
   ```

2. **Full-Text Search (FTS)**:
   ```python
   # BM25 keyword search
   results = table.search(query, query_type="fts").limit(k).to_list()
   ```

3. **Hybrid Search**:
   ```python
   # Get results from both
   vec_results = vector_search(query)
   fts_results = fts_search(query)

   # Combine with Reciprocal Rank Fusion (RRF)
   combined = reciprocal_rank_fusion(
       vec_results,
       fts_results,
       weights=[1-fts_weight, fts_weight]
   )
   ```

**Reciprocal Rank Fusion (RRF)**:
```python
def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)

# For each result
final_score = vec_weight * rrf_score(vec_rank) +
              fts_weight * rrf_score(fts_rank)
```

**Query Caching**:
- LRU cache with configurable size
- Cache key: (query, filters, mode)
- Invalidated on index updates

### 5. Result Enhancer (`ctxd/result_enhancer.py`)

Post-processes search results for better quality.

**Features**:

1. **De-duplication**:
   - Detects overlapping chunks from same file
   - Computes overlap percentage
   - Keeps highest-scoring chunk
   - Configurable overlap threshold

2. **Context Expansion**:
   - Reads source file
   - Includes N lines before/after chunk
   - Provides more context without re-indexing

3. **Recency Ranking**:
   - Boosts recently modified files
   - Used for tie-breaking
   - Configurable weight

**De-duplication Algorithm**:
```python
def deduplicate(chunks: List[Chunk]) -> List[Chunk]:
    result = []
    for chunk in sorted(chunks, key=lambda c: c.score, reverse=True):
        # Check if overlaps with already added chunks
        overlaps = [c for c in result if overlap_percentage(chunk, c) > threshold]
        if not overlaps:
            result.append(chunk)
    return result
```

### 6. MCP Server (`ctxd/mcp_server.py`)

Model Context Protocol server for Claude Code integration.

**Architecture**:
```
Claude Code <---MCP Protocol---> ctxd-mcp <---Python API---> Indexer/Store
```

**Tools Exposed**:

1. **ctx_search**: Search wrapper
   ```python
   @mcp.tool()
   def ctx_search(query: str, limit: int = 10, **filters):
       results = store.search(query, limit=limit, **filters)
       return format_results(results)
   ```

2. **ctx_status**: Index statistics
   ```python
   @mcp.tool()
   def ctx_status():
       stats = store.get_statistics()
       return format_statistics(stats)
   ```

3. **ctx_index**: Trigger indexing
   ```python
   @mcp.tool()
   def ctx_index(path: str = ".", force: bool = False):
       indexer.index_path(path, force=force)
       return get_index_stats()
   ```

**Communication**:
- Uses MCP SDK for protocol handling
- JSON-RPC over stdio
- Stateless request/response

### 7. File Watcher (`ctxd/watcher.py`)

Monitors filesystem for changes and triggers re-indexing.

**Implementation**:
- Uses watchdog library
- Debounced change detection
- Filters by ignore patterns
- Triggers incremental indexing

**Debouncing**:
```python
def on_file_change(path):
    # Reset debounce timer
    debounce_timer.reset()

    # When timer expires (no changes for N seconds)
    def on_debounce_expire():
        indexer.index_path(path, force=False)
```

## Data Flow

### Indexing Flow

```
1. User runs: ctxd index

2. Indexer.index_path()
   ├─> Discover files (git_utils)
   ├─> Filter (.gitignore + config patterns)
   ├─> For each file (parallel):
   │   ├─> Check file hash (incremental)
   │   ├─> Detect language
   │   ├─> Select chunker
   │   ├─> chunk_file() -> List[Chunk]
   │   └─> Accumulate chunks
   ├─> Batch embed chunks (embedding_model)
   ├─> Store chunks + embeddings (vector_store)
   └─> Cleanup deleted files

3. Store.add_chunks()
   ├─> Create/update LanceDB table
   ├─> Insert chunks with embeddings
   ├─> Create FTS index
   └─> Invalidate query cache
```

### Search Flow

```
1. User runs: ctxd search "query"

2. Store.search()
   ├─> Check query cache
   │   └─> If hit, return cached results
   ├─> Generate query embedding
   ├─> Execute search:
   │   ├─> Vector search (KNN)
   │   ├─> FTS search (BM25)
   │   └─> Hybrid: RRF combine
   ├─> Apply filters (extension, directory, etc.)
   └─> Return ranked results

3. ResultEnhancer.enhance()
   ├─> De-duplicate overlapping chunks
   ├─> Expand context from source files
   ├─> Apply recency boost
   └─> Return enhanced results

4. CLI displays results (syntax highlighted)
```

### MCP Flow

```
1. Claude Code makes MCP request:
   {"tool": "ctx_search", "query": "auth"}

2. MCP Server receives request
   ├─> Parse JSON-RPC
   ├─> Validate parameters
   └─> Call ctx_search()

3. ctx_search() delegates to Store
   └─> Store.search() (same as CLI)

4. Format results for MCP
   ├─> Convert to JSON
   ├─> Include metadata
   └─> Return to Claude Code

5. Claude Code uses results in context
```

## Storage Format

### LanceDB Structure

```
.ctxd/data.lance/
├── data/                      # Column-oriented data files
│   ├── _versions/             # Version tracking
│   ├── _indices/              # Vector indices
│   └── *.lance                # Data files
└── _metadata/                 # Table metadata
```

### File Hash Tracking

File hashes are stored in the database to enable incremental indexing:

```python
# Hash computation
import hashlib
def compute_hash(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# Incremental check
stored_hash = store.get_file_hash(file_path)
current_hash = compute_hash(file_path)
if stored_hash == current_hash:
    skip_indexing(file_path)
```

## Performance Optimizations

### 1. Parallel Processing

- **ThreadPoolExecutor** for file processing
- Thread-safe chunk accumulation
- Worker count = CPU cores (configurable)
- Speedup: ~4x on 8-core machines

### 2. Batch Embedding

- Generate embeddings in batches (default: 32)
- Reduces model loading overhead
- Better GPU utilization
- Speedup: ~10x vs. one-at-a-time

### 3. Query Caching

- LRU cache for search results
- Cache key: (query, filters, mode)
- Configurable size (default: 100)
- Speedup: ~100x for repeated queries

### 4. Incremental Indexing

- File hash comparison
- Only re-index changed files
- Typical re-index: <5 seconds
- Speedup: ~50x for unchanged codebases

### 5. Vector Index

- LanceDB uses IVF (Inverted File Index)
- Approximate nearest neighbor (ANN)
- Trade-off: speed vs. accuracy
- Speedup: ~100x vs. brute force on large datasets

## Language Support

### Supported Languages

| Language   | Chunker       | Chunk Types          |
|------------|---------------|----------------------|
| Python     | TreeSitter    | function, class      |
| JavaScript | TreeSitter    | function, class      |
| TypeScript | TreeSitter    | function, class      |
| Go         | TreeSitter    | function, method     |
| Markdown   | Markdown      | section              |
| Others     | Fallback      | paragraph            |

### Adding New Languages

To add TreeSitter support for a new language:

1. Install tree-sitter grammar:
   ```bash
   pip install tree-sitter-{language}
   ```

2. Update `treesitter.py`:
   ```python
   LANGUAGE_QUERIES = {
       "rust": {
           "function": "(function_item) @function",
           "struct": "(struct_item) @struct"
       }
   }
   ```

3. Add file extension mapping:
   ```python
   EXTENSIONS_TO_LANGUAGE = {
       ".rs": "rust"
   }
   ```

## Testing

ctxd has comprehensive test coverage:

```
tests/
├── test_indexer.py          # Indexing logic
├── test_store.py            # Vector store
├── test_chunkers.py         # All chunkers
├── test_embeddings.py       # Embedding model
├── test_result_enhancer.py  # Result enhancement
├── test_mcp.py              # MCP server
├── test_git_utils.py        # Git integration
└── fixtures/                # Test data
```

Run tests:
```bash
pytest --cov=ctxd
```

## Future Enhancements

Potential areas for improvement:

1. **More Languages**: Rust, Java, C++, Ruby tree-sitter support
2. **Reranking**: Use cross-encoder for better result ranking
3. **Clustering**: Group similar chunks for exploration
4. **Code Graph**: Build dependency graph from indexed code
5. **Incremental Embeddings**: Only re-embed changed chunks
6. **Distributed**: Index very large monorepos across machines

## References

- **LanceDB**: https://lancedb.github.io/lancedb/
- **Sentence Transformers**: https://www.sbert.net/
- **Tree-sitter**: https://tree-sitter.github.io/
- **Model Context Protocol**: https://spec.modelcontextprotocol.io/

## Next Steps

- [Configuration Guide](configuration.md) - Tune performance
- [API Reference](api.md) - Use ctxd programmatically
- [Usage Guide](usage.md) - CLI commands
