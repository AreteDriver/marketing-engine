"""Typer CLI for marketing engine."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import typer
from rich.console import Console

from marketing_engine import __version__
from marketing_engine.enums import ApprovalStatus, ContentStream
from marketing_engine.exceptions import MarketingEngineError

app = typer.Typer(
    name="marketing-engine",
    help="LLM-powered content pipeline for developer marketing.",
)
console = Console()


def _next_monday() -> date:
    """Return the date of next Monday."""
    today = date.today()
    days_ahead = 7 - today.weekday()  # 0=Monday
    if days_ahead == 7:
        days_ahead = 0
    return today + timedelta(days=days_ahead)


def _parse_date(value: str) -> date:
    """Parse a YYYY-MM-DD date string."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date format: {value}. Use YYYY-MM-DD.") from exc


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"marketing-engine v{__version__}")
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
    """Marketing Engine — LLM-powered content pipeline."""


@app.command()
def generate(
    week: str = typer.Option(
        "",
        "--week",
        help="Target week (YYYY-MM-DD Monday). Default: next Monday.",
    ),
    streams: str = typer.Option(
        "",
        "--streams",
        help="Comma-separated content streams to target.",
    ),
    activity: str = typer.Option(
        "",
        "--activity",
        help="Activity context: inline text or path to a text file.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run with mock LLM (no actual generation).",
    ),
) -> None:
    """Generate content for a week using the LLM pipeline."""
    from marketing_engine.config import (
        get_llm_model,
        get_llm_provider,
        load_brand_voice,
        load_platform_rules,
        load_schedule_rules,
    )
    from marketing_engine.db import get_database
    from marketing_engine.formatters import format_pipeline_summary
    from marketing_engine.pipeline import ContentPipeline

    try:
        week_of = _parse_date(week) if week else _next_monday()

        # Parse streams
        stream_list: list[ContentStream] | None = None
        if streams:
            stream_list = [ContentStream(s.strip()) for s in streams.split(",") if s.strip()]

        # Load activity from file if it's a path
        activity_text = activity
        if activity and Path(activity).exists():
            activity_text = Path(activity).read_text()

        # Load config
        try:
            brand_voice = load_brand_voice()
        except MarketingEngineError:
            brand_voice = {}
        try:
            platform_rules = load_platform_rules()
        except MarketingEngineError:
            platform_rules = {}
        try:
            schedule_rules = load_schedule_rules()
        except MarketingEngineError:
            schedule_rules = {}

        config = {
            "brand_voice": brand_voice,
            "platform_rules": platform_rules,
            "schedule_rules": schedule_rules,
        }

        # Select LLM
        if dry_run:
            import json

            from marketing_engine.llm.base import MockLLMClient

            mock_briefs = json.dumps(
                [
                    {
                        "topic": "Sample Topic",
                        "angle": "Demo angle for dry run",
                        "target_audience": "developers",
                        "relevant_links": [],
                        "stream": "project_marketing",
                        "platforms": ["twitter", "linkedin"],
                    }
                ]
            )
            mock_draft = json.dumps(
                {
                    "content": "This is a dry-run post. Replace with real LLM output.",
                    "cta_url": "https://example.com",
                    "hashtags": ["dryrun", "test"],
                }
            )
            mock_format = json.dumps(
                {
                    "content": "Dry-run formatted post.",
                    "hashtags": ["dryrun"],
                    "subreddit": None,
                }
            )
            llm = MockLLMClient([mock_briefs, mock_draft, mock_format])
        else:
            provider = get_llm_provider()
            if provider == "ollama":
                from marketing_engine.llm.ollama import OllamaClient

                llm = OllamaClient(model=get_llm_model())
            else:
                console.print(f"[red]Unsupported LLM provider: {provider}[/red]")
                raise typer.Exit(code=1)

        db = get_database()
        pipeline = ContentPipeline(db=db, llm=llm, config=config)

        console.print(f"[bold]Generating content for week of {week_of}...[/bold]")
        run = pipeline.run(week_of=week_of, streams=stream_list, activity=activity_text)
        format_pipeline_summary(run, console)

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def review(
    week: str = typer.Option(
        "",
        "--week",
        help="Target week (YYYY-MM-DD Monday). Default: next Monday.",
    ),
) -> None:
    """Interactive review of pending posts."""
    from marketing_engine.approval import approve_post, edit_post, reject_post
    from marketing_engine.db import get_database
    from marketing_engine.formatters import format_post_detail

    try:
        week_of = _parse_date(week) if week else _next_monday()
        db = get_database()
        pending = db.get_pending(week_of=week_of)

        if not pending:
            console.print("[yellow]No pending posts for this week.[/yellow]")
            return

        console.print(f"[bold]{len(pending)} pending post(s) for week of {week_of}[/bold]")
        console.print()

        for post in pending:
            format_post_detail(post, console)
            console.print()

            while True:
                action = (
                    console.input("[bold][a]pprove / [e]dit / [r]eject / [s]kip / [q]uit: [/bold]")
                    .strip()
                    .lower()
                )

                if action in ("a", "approve"):
                    approve_post(db, post.id)
                    console.print("[green]Approved.[/green]")
                    break
                elif action in ("e", "edit"):
                    new_content = console.input("[bold]New content: [/bold]")
                    edit_post(db, post.id, new_content)
                    console.print("[cyan]Edited and approved.[/cyan]")
                    break
                elif action in ("r", "reject"):
                    reason = console.input(
                        "[bold]Rejection reason (Enter to skip): [/bold]"
                    ).strip()
                    reject_post(db, post.id, reason or None)
                    console.print("[red]Rejected.[/red]")
                    break
                elif action in ("s", "skip"):
                    console.print("[yellow]Skipped.[/yellow]")
                    break
                elif action in ("q", "quit"):
                    console.print("Review ended.")
                    return
                else:
                    console.print("[yellow]Invalid choice. Use a/e/r/s/q.[/yellow]")

        console.print("[bold]Review complete.[/bold]")

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def approve(
    post_id: str = typer.Argument(..., help="Post ID to approve."),
) -> None:
    """Approve a single post by ID."""
    from marketing_engine.approval import approve_post as do_approve
    from marketing_engine.db import get_database
    from marketing_engine.formatters import format_post_detail

    try:
        db = get_database()
        post = do_approve(db, post_id)
        console.print("[green]Post approved.[/green]")
        format_post_detail(post, console)
    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def edit(
    post_id: str = typer.Argument(..., help="Post ID to edit."),
) -> None:
    """Edit a post's content interactively."""
    from marketing_engine.approval import edit_post as do_edit
    from marketing_engine.db import get_database
    from marketing_engine.formatters import format_post_detail

    try:
        db = get_database()
        existing = db.get_post(post_id)
        if existing is None:
            console.print(f"[red]Post not found: {post_id}[/red]")
            raise typer.Exit(code=1)

        console.print("[bold]Current content:[/bold]")
        console.print(existing.edited_content or existing.content)
        console.print()
        new_content = console.input("[bold]New content: [/bold]")
        post = do_edit(db, post_id, new_content)
        console.print("[cyan]Post edited.[/cyan]")
        format_post_detail(post, console)
    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def reject(
    post_id: str = typer.Argument(..., help="Post ID to reject."),
    reason: str | None = typer.Option(None, "--reason", "-r", help="Rejection reason."),
) -> None:
    """Reject a post with an optional reason."""
    from marketing_engine.approval import reject_post as do_reject
    from marketing_engine.db import get_database
    from marketing_engine.formatters import format_post_detail

    try:
        db = get_database()
        post = do_reject(db, post_id, reason)
        console.print("[red]Post rejected.[/red]")
        format_post_detail(post, console)
    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def queue(
    week: str = typer.Option(
        "",
        "--week",
        help="Target week (YYYY-MM-DD Monday). Default: next Monday.",
    ),
    status: str = typer.Option(
        "all",
        "--status",
        help="Filter by status: pending, approved, rejected, edited, all.",
    ),
) -> None:
    """Show the content queue for a week."""
    from marketing_engine.db import get_database
    from marketing_engine.formatters import format_queue_table

    try:
        week_of = _parse_date(week) if week else _next_monday()
        db = get_database()
        posts = db.get_queue(week_of)

        if status != "all":
            try:
                filter_status = ApprovalStatus(status)
            except ValueError:
                console.print(
                    f"[red]Invalid status: {status}. "
                    f"Use pending/approved/rejected/edited/all.[/red]"
                )
                raise typer.Exit(code=1) from None
            posts = [p for p in posts if p.approval_status == filter_status]

        if not posts:
            console.print(
                f"[yellow]No posts found for week of {week_of}"
                f"{f' with status {status}' if status != 'all' else ''}.[/yellow]"
            )
            return

        format_queue_table(posts, console)

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command(name="export")
def export_cmd(
    week: str = typer.Option(
        "",
        "--week",
        help="Target week (YYYY-MM-DD Monday). Default: next Monday.",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. Default: stdout.",
    ),
) -> None:
    """Export approved posts to JSON or Markdown."""
    from marketing_engine.db import get_database
    from marketing_engine.export import export_approved

    try:
        week_of = _parse_date(week) if week else _next_monday()
        db = get_database()
        result = export_approved(db, week_of, fmt=fmt)

        if output:
            Path(output).write_text(result)
            console.print(f"[green]Exported to {output}[/green]")
        else:
            console.print(result)

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of runs to show."),
) -> None:
    """Show recent pipeline run history."""
    from rich.table import Table
    from rich.text import Text

    from marketing_engine.db import get_database

    try:
        db = get_database()
        runs = db.get_pipeline_runs(limit=limit)

        if not runs:
            console.print("[yellow]No pipeline runs found.[/yellow]")
            return

        table = Table(title="Pipeline Run History", show_lines=True)
        table.add_column("ID", min_width=10)
        table.add_column("Week", min_width=10)
        table.add_column("Status", min_width=10)
        table.add_column("Briefs", justify="right")
        table.add_column("Drafts", justify="right")
        table.add_column("Posts", justify="right")
        table.add_column("Started", min_width=19)
        table.add_column("Duration")

        for run in runs:
            status_color = "green" if run.status == "completed" else "red"
            duration = ""
            if run.completed_at:
                delta = run.completed_at - run.started_at
                duration = f"{delta.total_seconds():.1f}s"

            table.add_row(
                run.id[:8] + "...",
                run.week_of.isoformat(),
                Text(run.status, style=status_color),
                str(run.briefs_count),
                str(run.drafts_count),
                str(run.posts_count),
                run.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                duration,
            )

        console.print(table)

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def status() -> None:
    """Show current configuration and license status."""
    from rich.table import Table

    from marketing_engine.config import get_config_dir, get_db_path, get_llm_model, get_llm_provider
    from marketing_engine.licensing import FREE_FEATURES, PRO_FEATURES, get_license

    key, tier = get_license()

    table = Table(title="Marketing Engine Status", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Version", __version__)
    table.add_row("License Tier", tier)
    table.add_row("License Key", (key[:12] + "...") if key else "None (Free tier)")
    table.add_row("Config Dir", str(get_config_dir()))
    table.add_row("Database", str(get_db_path()))
    table.add_row("LLM Provider", get_llm_provider())
    table.add_row("LLM Model", get_llm_model())

    # Features
    all_features = sorted(FREE_FEATURES | PRO_FEATURES)
    from marketing_engine.licensing import has_feature

    feature_lines = []
    for feat in all_features:
        check = "[green]Y[/green]" if has_feature(feat) else "[red]N[/red]"
        feature_lines.append(f"  {check} {feat}")
    table.add_row("Features", "\n".join(feature_lines))

    console.print(table)


@app.command()
def init() -> None:
    """Initialize configuration directory and default files."""

    from marketing_engine.config import get_config_dir, get_db_path

    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Config directory: {config_dir}[/green]")

    # Create default YAML files if they don't exist
    defaults = {
        "brand_voice.yaml": _DEFAULT_BRAND_VOICE,
        "platform_rules.yaml": _DEFAULT_PLATFORM_RULES,
        "schedule_rules.yaml": _DEFAULT_SCHEDULE_RULES,
    }
    for filename, content in defaults.items():
        filepath = config_dir / filename
        if not filepath.exists():
            filepath.write_text(content)
            console.print(f"  Created {filepath}")
        else:
            console.print(f"  [yellow]Exists: {filepath}[/yellow]")

    # Ensure DB directory exists
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Database directory: {db_path.parent}[/green]")
    console.print("[bold]Initialization complete.[/bold]")


@app.command()
def publish(
    week: str = typer.Option(
        "",
        "--week",
        help="Target week (YYYY-MM-DD Monday). Default: next Monday.",
    ),
    platform: str = typer.Option(
        "",
        "--platform",
        help="Filter by platform (twitter, linkedin, reddit).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate publishing without making API calls.",
    ),
    all_approved: bool = typer.Option(
        False,
        "--all",
        help="Publish all approved posts, not just due ones.",
    ),
) -> None:
    """Publish approved posts to platforms."""
    from marketing_engine.db import get_database
    from marketing_engine.licensing import require_feature
    from marketing_engine.publishers.scheduler import publish_due_posts

    try:
        if not dry_run:
            require_feature("publish")

        db = get_database()

        if all_approved:
            week_of = _parse_date(week) if week else _next_monday()
            posts = db.get_queue(week_of)
            posts = [
                p
                for p in posts
                if p.approval_status in (ApprovalStatus.approved, ApprovalStatus.edited)
            ]
        else:
            posts = None  # scheduler handles query

        if platform:
            from marketing_engine.enums import Platform

            try:
                Platform(platform)
            except ValueError:
                console.print(f"[red]Invalid platform: {platform}[/red]")
                raise typer.Exit(code=1) from None

        results = publish_due_posts(db, dry_run=dry_run)

        if not results:
            console.print("[yellow]No posts due for publishing.[/yellow]")
            return

        for r in results:
            if r.success:
                console.print(f"[green]Published[/green] {r.platform} → {r.post_url or 'OK'}")
            else:
                console.print(f"[red]Failed[/red] {r.platform}: {r.error}")

        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        console.print(f"\n[bold]{ok} published, {fail} failed[/bold]")

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command(name="publish-one")
def publish_one(
    post_id: str = typer.Argument(..., help="Post ID to publish."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate publishing without making API calls.",
    ),
) -> None:
    """Publish a single post by ID."""
    from marketing_engine.db import get_database
    from marketing_engine.licensing import require_feature
    from marketing_engine.publishers.scheduler import publish_single

    try:
        if not dry_run:
            require_feature("publish")

        db = get_database()
        result = publish_single(db, post_id, dry_run=dry_run)

        if result.success:
            console.print(f"[green]Published[/green] {result.platform} → {result.post_url or 'OK'}")
        else:
            console.print(f"[red]Failed[/red] {result.platform}: {result.error}")

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command(name="publish-status")
def publish_status_cmd(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show."),
) -> None:
    """Show recent publish history."""
    from rich.table import Table
    from rich.text import Text

    from marketing_engine.db import get_database

    try:
        db = get_database()
        history = db.get_publish_history(limit=limit)

        if not history:
            console.print("[yellow]No publish history found.[/yellow]")
            return

        table = Table(title="Publish History", show_lines=True)
        table.add_column("Post ID", min_width=10)
        table.add_column("Platform", min_width=8)
        table.add_column("Status", min_width=10)
        table.add_column("URL")
        table.add_column("Published At", min_width=19)
        table.add_column("Error")

        for entry in history:
            status_color = "green" if entry["status"] == "published" else "red"
            table.add_row(
                (entry["post_id"][:8] + "...") if entry["post_id"] else "",
                entry.get("platform", ""),
                Text(entry.get("status", ""), style=status_color),
                entry.get("post_url", "") or "",
                entry.get("published_at", "") or "",
                entry.get("error", "") or "",
            )

        console.print(table)

    except MarketingEngineError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


_DEFAULT_BRAND_VOICE = """\
# Brand Voice Configuration
avoid:
  - "excited to announce"
  - "game-changer"
  - "leveraging AI"
  - "revolutionary"
  - "synergy"
  - "delighted to share"
  - "thrilled"

principles:
  - "Be direct and specific"
  - "Show results, not promises"
  - "Include a clear call to action"
  - "Write like a human, not a press release"
  - "Lead with value, not hype"

stream_tones:
  project_marketing: "Professional but approachable. Technical depth without jargon."
  benchgoblins: "Casual and fun. Fantasy sports energy."
  eve_content: "In-universe immersion. Community engagement."
  linux_tools: "Practical and direct. Demo-oriented."
  technical_ai: "Thought leadership. Deep technical insight."
"""

_DEFAULT_PLATFORM_RULES = """\
# Platform-Specific Rules
twitter:
  max_chars: 280
  max_hashtags: 3
  style_notes: "Short, punchy. Thread for longer content. Use line breaks."

linkedin:
  max_chars: 3000
  max_hashtags: 5
  style_notes: "Professional tone. Use bullet points. Hook in first line."

reddit:
  max_chars: 10000
  max_hashtags: 0
  style_notes: "No hashtags. Conversational. Match subreddit culture. Self-posts preferred."

youtube:
  max_chars: 5000
  max_hashtags: 15
  style_notes: "Description optimized for SEO. Timestamps if applicable."

tiktok:
  max_chars: 2200
  max_hashtags: 5
  style_notes: "Casual, hook-driven. Trending sounds/hashtags when relevant."
"""

_DEFAULT_SCHEDULE_RULES = """\
# Schedule Rules
timezone: "America/New_York"

# 0=Monday, 6=Sunday
posting_days: [1, 2, 3, 4, 5, 6]

posting_windows:
  twitter:
    - {hour: 9, minute: 0}
    - {hour: 12, minute: 30}
    - {hour: 17, minute: 0}
  linkedin:
    - {hour: 8, minute: 0}
    - {hour: 12, minute: 0}
    - {hour: 17, minute: 30}
  reddit:
    - {hour: 10, minute: 0}
    - {hour: 14, minute: 0}
    - {hour: 19, minute: 0}
  youtube:
    - {hour: 10, minute: 0}
    - {hour: 15, minute: 0}
  tiktok:
    - {hour: 11, minute: 0}
    - {hour: 19, minute: 0}
    - {hour: 21, minute: 0}
"""
