"""Timeless Clips CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from timeless_clips import __version__

app = typer.Typer(
    name="timeless-clips",
    help="Public domain clips reimagined as viral Shorts.",
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"timeless-clips v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Timeless Clips -- Public domain Shorts pipeline."""


@app.command()
def discover(
    category: str = typer.Argument(
        ...,
        help="Category: ads, educational, film, speech, nasa, newsreel",
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results to fetch."),
    config: str = typer.Option("", "--config", "-c", help="Config YAML path."),
) -> None:
    """Discover content from the Internet Archive."""
    from timeless_clips.config import load_config
    from timeless_clips.pipeline import TimelessClipsPipeline

    cfg = load_config(Path(config) if config else None)
    pipeline = TimelessClipsPipeline(config=cfg)
    count = pipeline.discover(category, max_results=limit)
    console.print(f"[green]Discovered {count} new items in '{category}'[/green]")


@app.command()
def process(
    category: str = typer.Option("", "--category", "-c", help="Filter by category."),
    batch: int = typer.Option(5, "--batch", "-b", help="Batch size."),
    identifier: str = typer.Option("", "--identifier", "-i", help="Process a single item by ID."),
    config: str = typer.Option("", "--config", help="Config YAML path."),
) -> None:
    """Process items into Shorts."""
    from timeless_clips.config import load_config
    from timeless_clips.pipeline import TimelessClipsPipeline

    cfg = load_config(Path(config) if config else None)
    pipeline = TimelessClipsPipeline(config=cfg)

    if identifier:
        item = pipeline._catalog.get_item(identifier)
        if item is None:
            console.print(f"[red]Item not found: {identifier}[/red]")
            raise typer.Exit(code=1)
        try:
            path = pipeline.process_single(item)
            console.print(f"[green]Short created: {path}[/green]")
        except Exception as exc:
            console.print(f"[red]Failed: {exc}[/red]")
            raise typer.Exit(code=1) from exc
    else:
        cat = category or None
        results = pipeline.process_batch(category=cat, batch_size=batch)
        console.print(f"[green]Processed {len(results)} Shorts[/green]")
        for p in results:
            console.print(f"  {p}")


@app.command()
def catalog(
    config: str = typer.Option("", "--config", help="Config YAML path."),
) -> None:
    """Show catalog statistics."""
    from timeless_clips.config import load_config
    from timeless_clips.pipeline import TimelessClipsPipeline

    cfg = load_config(Path(config) if config else None)
    pipeline = TimelessClipsPipeline(config=cfg)
    stats = pipeline.get_stats()

    table = Table(title="Catalog Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total items", str(stats["total"]))
    table.add_row("Processed", str(stats["processed"]))
    table.add_row("Unprocessed", str(stats["unprocessed"]))

    console.print(table)

    if stats["by_category"]:
        cat_table = Table(title="By Category")
        cat_table.add_column("Category")
        cat_table.add_column("Count", justify="right")
        for cat, cnt in sorted(stats["by_category"].items()):
            cat_table.add_row(cat, str(cnt))
        console.print(cat_table)

    if stats["by_collection"]:
        col_table = Table(title="By Collection")
        col_table.add_column("Collection")
        col_table.add_column("Count", justify="right")
        for col, cnt in sorted(stats["by_collection"].items()):
            col_table.add_row(col, str(cnt))
        console.print(col_table)


@app.command()
def init(
    config: str = typer.Option("", "--config", help="Config YAML path to create."),
) -> None:
    """Initialize config and directory structure."""
    import yaml

    from timeless_clips.config import _DEFAULTS

    config_path = Path(config) if config else Path("configs/config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(yaml.dump(_DEFAULTS, default_flow_style=False))
        console.print(f"[green]Created config: {config_path}[/green]")
    else:
        console.print(f"[yellow]Config exists: {config_path}[/yellow]")

    for d in ["cache", "output"]:
        Path(d).mkdir(exist_ok=True)
        console.print(f"[green]Created directory: {d}/[/green]")

    console.print("[bold]Initialization complete.[/bold]")
