# ctxd Documentation

This is the main documentation for ctxd, a local-first semantic code search daemon.

## Getting Started

To get started with ctxd, you'll need to install it first.

### Installation

You can install ctxd using pip:

```bash
pip install ctxd
```

### Configuration

Create a configuration file at `.ctxd/config.toml`:

```toml
[indexer]
exclude = ["node_modules", "*.min.js"]
max_file_size = 1048576

[embeddings]
model = "all-MiniLM-L6-v2"
```

## Usage

Basic usage of ctxd involves indexing your codebase and then searching it.

### Indexing

Run the indexer on your project:

```bash
ctxd index .
```

### Searching

Search for code snippets:

```bash
ctxd search "function to handle authentication"
```

## Advanced Features

ctxd supports several advanced features.

### Multi-language Support

ctxd supports multiple programming languages:
- Python
- JavaScript/TypeScript
- Go
- Markdown

### Real-time Watching

Enable file watching for automatic re-indexing:

```bash
ctxd watch
```

## API Reference

### Core Functions

The main API functions are documented here.

## Contributing

We welcome contributions! Please see our contributing guide.

### Development Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/user/ctxd.git
cd ctxd
pip install -e ".[dev]"
```

### Running Tests

Execute the test suite:

```bash
pytest tests/
```

## License

MIT License - see LICENSE file for details.
