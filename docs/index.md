# ctxd Documentation

**Local-first semantic code search daemon for AI coding assistants**

## What is ctxd?

ctxd (pronounced "context-d") is a semantic code search tool that indexes your codebase into a local vector database, enabling AI assistants like Claude Code to query relevant code snippets without loading entire directory structures into context. This dramatically reduces token usage (target: ~40% reduction) while improving code understanding.

## Key Benefits

- **Reduced Token Usage**: Search through thousands of files without loading them all into context
- **Semantic Understanding**: Find code by what it does, not just what it's named
- **Local-First**: All data stays on your machine - no cloud dependencies or privacy concerns
- **Fast & Incremental**: Only re-indexes changed files for quick updates
- **AI-Native**: Built specifically for integration with AI coding assistants via MCP

## How It Works

1. **Index**: ctxd scans your codebase and breaks it into semantic chunks (functions, classes, etc.)
2. **Embed**: Each chunk is converted into a vector representation using local ML models
3. **Store**: Vectors are stored in a local LanceDB database
4. **Search**: AI assistants can search semantically ("find authentication logic") or by keywords
5. **Retrieve**: Only relevant code snippets are loaded into context, saving tokens

## Features at a Glance

### Search Capabilities
- **Hybrid Search**: Combines semantic (vector) and keyword (BM25) search for best results
- **Rich Filtering**: Filter by file extension, directory, chunk type, language, and git branch
- **Result Enhancement**: Automatic de-duplication, context expansion, and recency ranking

### Code Understanding
- **Multi-Language Support**: AST-based chunking for Python, JavaScript, TypeScript, Go, and Markdown
- **Smart Chunking**: Extracts functions, classes, and methods as semantic units
- **Context Preservation**: Includes docstrings, decorators, and surrounding context

### Developer Experience
- **CLI Interface**: Full-featured command-line interface for manual usage
- **MCP Integration**: Native integration with Claude Code via Model Context Protocol
- **File System Watching**: Automatic re-indexing when files change
- **Beautiful Output**: Syntax-highlighted search results with progress bars

### Performance
- **Parallel Processing**: Multi-threaded file processing for fast indexing
- **Batch Embeddings**: Generate embeddings in batches for efficiency
- **Query Caching**: LRU cache for faster repeated searches
- **Incremental Updates**: Only re-index files that have changed

## Quick Links

- [Installation Guide](installation.md) - Get started with ctxd
- [Quick Start](quickstart.md) - Index and search your first codebase
- [Usage Guide](usage.md) - Detailed command reference
- [MCP Integration](mcp-integration.md) - Connect ctxd to Claude Code
- [Configuration](configuration.md) - Customize ctxd's behavior
- [Architecture](architecture.md) - How ctxd works under the hood
- [API Reference](api.md) - Python API documentation

## Use Cases

### For AI Assistants
- Find relevant code examples without scanning entire projects
- Understand codebase patterns and architecture quickly
- Locate specific implementations across large repositories
- Reduce context window usage by 40% or more

### For Developers
- Semantic code search: "find error handling logic"
- Cross-reference similar implementations
- Discover related code across the project
- Navigate unfamiliar codebases efficiently

## System Requirements

- **Python**: 3.10 or higher
- **Platform**: Linux, macOS, or Windows
- **Memory**: 2GB+ recommended for large codebases
- **Disk Space**: ~10-50MB per 10,000 files indexed (varies by code density)

## License

[License information to be added]

## Contributing

Contributions are welcome! Please see our [GitHub repository](https://github.com/yourusername/ctxd) for more information.

## Next Steps

Ready to get started? Head to the [Installation Guide](installation.md) to install ctxd, or jump straight to the [Quick Start](quickstart.md) guide.
