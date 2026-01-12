"""
Command-line interface for ctxd.

Provides commands for initializing, indexing, searching, and managing
the code index.
"""

import logging
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table

from .config import Config
from .store import VectorStore
from .embeddings import EmbeddingModel
from .indexer import Indexer
from .progress import ProgressReporter
from . import __version__

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.version_option(version=__version__, prog_name="ctxd")
def main(debug: bool):
    """ctxd - Local-first semantic code search for AI coding assistants."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


@main.command()
@click.option("--path", "-p", default=".", help="Project root path")
def init(path: str):
    """Initialize ctxd in the current project."""
    project_root = Path(path).resolve()

    # Create .ctxd directory
    ctxd_dir = project_root / ".ctxd"
    if ctxd_dir.exists():
        console.print(f"[yellow].ctxd directory already exists at {ctxd_dir}[/yellow]")
        return

    ctxd_dir.mkdir(parents=True, exist_ok=True)

    # Create default config file
    config_path = ctxd_dir / "config.toml"
    config_content = """# ctxd configuration

[indexer]
exclude = [
    "node_modules",
    "*.min.js",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    "*.pyc",
    ".git",
    ".ctxd",
    ".ctxcache",
]
max_file_size = 1048576  # 1MB
max_chunk_size = 500
chunk_overlap = 50

[embeddings]
model = "all-MiniLM-L6-v2"
batch_size = 32

[search]
default_limit = 10
min_score = 0.3

# Phase 4: Hybrid search
mode = "hybrid"           # "vector", "fts", or "hybrid"
fts_weight = 0.5          # BM25 weight for hybrid mode (0.0-1.0)

# Phase 4: Result enhancement
deduplicate = true        # Remove overlapping chunks from same file
overlap_threshold = 0.5   # Overlap percentage threshold (0.0-1.0)
expand_context = false    # Include surrounding lines from source files
context_lines_before = 3  # Lines to include before chunk
context_lines_after = 3   # Lines to include after chunk
recency_weight = 0.1      # Recency boost for tie-breaking (0.0-1.0)

[git]
# Enable git integration (branch tracking)
enabled = true

# Auto-cleanup deleted files on re-index
cleanup_deleted = true

# Support nested .gitignore files
nested_gitignore = true
"""
    config_path.write_text(config_content)

    console.print(f"[green]✓[/green] Initialized ctxd at {project_root}")
    console.print(f"[green]✓[/green] Created config at {config_path}")
    console.print("\nNext steps:")
    console.print("  1. Run [cyan]ctxd index[/cyan] to index your codebase")
    console.print("  2. Run [cyan]ctxd search <query>[/cyan] to search your code")


@main.command()
@click.argument("path", default=".")
@click.option("--force", "-f", is_flag=True, help="Force re-indexing of all files")
@click.option("--branch", "-b", help="Git branch to tag chunks with (auto-detected if not specified)")
def index(path: str, force: bool, branch: str):
    """Index a codebase for semantic search."""
    index_path = Path(path).resolve()

    if not index_path.exists():
        console.print(f"[red]Error: Path does not exist: {index_path}[/red]")
        sys.exit(1)

    # Determine project root (for .ctxd directory)
    # If indexing a file, use current directory as project root
    # If indexing a directory, use that as project root
    if index_path.is_file():
        project_root = Path.cwd()
    else:
        project_root = index_path

    # Initialize components
    config = Config(project_root)
    db_path = project_root / ".ctxd" / "data.lance"
    store = VectorStore(db_path)
    embeddings = EmbeddingModel(
        model_name=config.get("embeddings", "model", default="all-MiniLM-L6-v2")
    )
    indexer = Indexer(store, embeddings, config)

    console.print(f"[cyan]Indexing {index_path}...[/cyan]")

    # Create progress tracker with ETA
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TextColumn("[cyan]ETA: {task.fields[eta]}"),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing files...", total=0, eta="calculating...")

        def progress_callback(event):
            """Handle progress events with ETA."""
            eta_str = ProgressReporter.format_eta(event.eta_seconds)
            progress.update(
                task,
                total=event.total,
                completed=event.current,
                description=f"Indexing: {Path(event.filename).name}",
                eta=eta_str
            )

        try:
            stats = indexer.index_path(
                index_path,
                force=force,
                branch=branch,
                progress_callback=progress_callback
            )

            # Display results
            console.print("\n[green]✓ Indexing complete![/green]\n")
            console.print(str(stats))

        except Exception as e:
            console.print(f"\n[red]Error during indexing: {e}[/red]")
            if logger.isEnabledFor(logging.DEBUG):
                raise
            sys.exit(1)


@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Maximum number of results")
@click.option("--file", "-f", help="Filter results by file pattern")
@click.option("--branch", "-b", help="Filter results by git branch")
@click.option("--ext", "-e", multiple=True, help="Filter by file extension (e.g., .py, .js)")
@click.option("--dir", "-d", multiple=True, help="Filter by directory prefix (e.g., src/, lib/)")
@click.option("--type", "-t", multiple=True, help="Filter by chunk type (function, class, block)")
@click.option("--lang", "-l", multiple=True, help="Filter by language (python, javascript, etc.)")
@click.option("--mode", "-m", type=click.Choice(["vector", "fts", "hybrid"]), help="Search mode (default: hybrid)")
@click.option("--no-dedup", is_flag=True, help="Disable de-duplication of overlapping chunks")
@click.option("--expand", is_flag=True, help="Expand results with surrounding context lines")
def search(query: str, limit: int, file: str, branch: str, ext: tuple, dir: tuple, type: tuple, lang: tuple, mode: str, no_dedup: bool, expand: bool):
    """Search the indexed codebase semantically.

    Examples:
      ctxd search "authentication logic"
      ctxd search "error handling" --ext .py --dir src/
      ctxd search "database" --type function --lang python
      ctxd search "LoginButton" --mode fts --expand
    """
    project_root = Path.cwd()

    # Initialize components
    config = Config(project_root)
    db_path = project_root / ".ctxd" / "data.lance"

    if not db_path.exists():
        console.print("[red]Error: No index found. Run 'ctxd index' first.[/red]")
        sys.exit(1)

    store = VectorStore(db_path)
    embeddings = EmbeddingModel(
        model_name=config.get("embeddings", "model", default="all-MiniLM-L6-v2")
    )

    # Determine search mode from config or option
    search_mode = mode or config.get("search", "mode", default="hybrid")

    # Show search info
    mode_desc = {
        "vector": "semantic (vector)",
        "fts": "keyword (BM25)",
        "hybrid": "hybrid (vector + keyword)"
    }
    console.print(f'[cyan]Searching ({mode_desc.get(search_mode, search_mode)}):[/cyan] "{query}"\n')

    try:
        # Generate query embedding for vector/hybrid modes
        query_vector = None
        if search_mode in ["vector", "hybrid"]:
            query_vector = embeddings.embed_text(query)

        # Prepare filters
        extensions = list(ext) if ext else None
        directories = list(dir) if dir else None
        chunk_types = list(type) if type else None
        languages = list(lang) if lang else None

        # Get search limit (request more if deduplication is enabled)
        should_dedup = not no_dedup and config.get("search", "deduplicate", default=True)
        search_limit = limit * 2 if should_dedup else limit

        # Search
        results = store.search(
            query_vector=query_vector,
            query_text=query,
            limit=search_limit,
            mode=search_mode,
            file_filter=file,
            branch_filter=branch,
            extensions=extensions,
            directories=directories,
            chunk_types=chunk_types,
            languages=languages,
            min_score=config.get("search", "min_score", default=0.3)
        )

        # Apply result enhancements
        if results:
            from .result_enhancer import ResultEnhancer
            enhancer = ResultEnhancer()

            # De-duplicate
            if should_dedup:
                overlap_threshold = config.get("search", "overlap_threshold", default=0.5)
                results = enhancer.deduplicate(results, overlap_threshold=overlap_threshold)

            # Recency ranking
            recency_weight = config.get("search", "recency_weight", default=0.1)
            results = enhancer.rerank_by_recency(results, recency_weight=recency_weight)

            # Trim to requested limit
            results = results[:limit]

            # Expand context if requested
            if expand:
                lines_before = config.get("search", "context_lines_before", default=3)
                lines_after = config.get("search", "context_lines_after", default=3)
                results = enhancer.expand_context(
                    results,
                    lines_before=lines_before,
                    lines_after=lines_after,
                    project_root=project_root
                )

        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        # Display results
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            score = result.score

            # Create a table for each result
            table = Table(show_header=False, box=None, padding=(0, 1))

            # Header: rank, file, lines, score
            header = f"[bold]{i}. {chunk.path}:{chunk.start_line}-{chunk.end_line}[/bold] [dim](score: {score:.3f})[/dim]"
            if chunk.name:
                header += f" [cyan]{chunk.chunk_type}: {chunk.name}[/cyan]"

            console.print(header)

            # Code snippet with syntax highlighting
            syntax = Syntax(
                chunk.text,
                chunk.language,
                theme="monokai",
                line_numbers=True,
                start_line=chunk.start_line,
            )
            console.print(syntax)
            console.print()  # Add spacing

    except Exception as e:
        console.print(f"[red]Error during search: {e}[/red]")
        if logger.isEnabledFor(logging.DEBUG):
            raise
        sys.exit(1)


@main.command()
def status():
    """Show indexing statistics."""
    project_root = Path.cwd()

    # Initialize store
    db_path = project_root / ".ctxd" / "data.lance"

    if not db_path.exists():
        console.print("[yellow]No index found. Run 'ctxd index' to create one.[/yellow]")
        return

    try:
        store = VectorStore(db_path)
        stats = store.get_stats()

        # Display stats in a nice table
        table = Table(title="Index Statistics", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total files", str(stats.total_files))
        table.add_row("Total chunks", str(stats.total_chunks))
        table.add_row("Index size", f"{stats.total_size_bytes / 1024 / 1024:.2f} MB")

        if stats.last_indexed:
            import datetime
            dt = datetime.datetime.fromtimestamp(stats.last_indexed)
            table.add_row("Last indexed", dt.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)

        # Language breakdown
        if stats.languages:
            console.print("\n[bold]Languages:[/bold]")
            for lang, count in sorted(stats.languages.items(), key=lambda x: -x[1]):
                console.print(f"  {lang}: {count}")

    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")
        if logger.isEnabledFor(logging.DEBUG):
            raise
        sys.exit(1)


@main.command()
@click.confirmation_option(prompt="Are you sure you want to delete all indexed data?")
def clean():
    """Remove all indexed data."""
    project_root = Path.cwd()
    db_path = project_root / ".ctxd" / "data.lance"

    if not db_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    try:
        store = VectorStore(db_path)
        store.clear_all()
        console.print("[green]✓ Cleared all indexed data.[/green]")
    except Exception as e:
        console.print(f"[red]Error cleaning index: {e}[/red]")
        sys.exit(1)


@main.command()
def version():
    """Show ctxd version."""
    console.print(f"ctxd version {__version__}")


if __name__ == "__main__":
    main()
