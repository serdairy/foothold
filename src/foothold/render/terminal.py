"""Rich terminal output."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from foothold.focus import Focus
from foothold.models import RepoMap


def render_map(repo: RepoMap, top: int, console: Console | None = None) -> None:
    console = console or Console()
    sources = [m for m in repo.modules.values() if not m.is_test]
    tests = len(repo.modules) - len(sources)
    console.print(
        f"[bold]{len(repo.modules)}[/bold] modules "
        f"([bold]{len(sources)}[/bold] source, [bold]{tests}[/bold] test) · "
        f"[bold]{repo.loc_total:,}[/bold] lines · "
        f"[bold]{len(repo.edges)}[/bold] import statements"
    )

    table = Table(title=f"Top {top} files by structural weight", title_justify="left")
    table.add_column("#", justify="right", style="dim")
    table.add_column("file")
    table.add_column("score", justify="right")
    table.add_column("in", justify="right")
    table.add_column("loc", justify="right")
    table.add_column("why", style="dim")
    for i, score in enumerate(repo.scores[:top], start=1):
        table.add_row(
            str(i),
            score.path,
            f"{score.total:.3f}",
            str(score.fan_in),
            str(score.loc),
            ", ".join(score.reasons) or "—",
        )
    console.print(table)

    if repo.entrypoints:
        console.print("\n[bold]Entry points[/bold] (imported by nothing in-project)")
        for name in repo.entrypoints[:8]:
            console.print(f"  · {repo.modules[name].path}")
    if repo.cycles:
        console.print(f"\n[bold yellow]{len(repo.cycles)} import cycle(s)[/bold yellow]")
        for cycle in repo.cycles[:3]:
            console.print(f"  · {' → '.join([*cycle, cycle[0]])}")


def render_focus(repo: RepoMap, focus: Focus, top: int, console: Console | None = None) -> None:
    """Print the diff-scoped reading path: what changed, then what depends on it."""
    console = console or Console()
    console.print(
        f"[bold]{len(focus.changed)}[/bold] changed source file(s) · "
        f"[bold]{len(focus.dependents)}[/bold] file(s) importing them · "
        f"[bold]{len(focus.changed_tests)}[/bold] changed test file(s)"
    )

    if focus.changed:
        table = Table(title="Changed, by structural weight", title_justify="left")
        table.add_column("#", justify="right", style="dim")
        table.add_column("file")
        table.add_column("score", justify="right")
        table.add_column("in", justify="right")
        table.add_column("loc", justify="right")
        for i, score in enumerate(focus.changed[:top], start=1):
            table.add_row(
                str(i), score.path, f"{score.total:.3f}", str(score.fan_in), str(score.loc)
            )
        console.print(table)

    if focus.dependents:
        table = Table(title="Read next: these import what changed", title_justify="left")
        table.add_column("#", justify="right", style="dim")
        table.add_column("file")
        table.add_column("score", justify="right")
        table.add_column("why", style="dim")
        for i, score in enumerate(focus.dependents[:top], start=1):
            table.add_row(str(i), score.path, f"{score.total:.3f}", ", ".join(score.reasons) or "—")
        console.print(table)

    if focus.changed_tests:
        console.print("\n[bold]Tests touched[/bold] [dim](not ranked; tests are excluded)[/dim]")
        for path in focus.changed_tests[:top]:
            console.print(f"  · {path}")

    if focus.unranked:
        shown = ", ".join(focus.unranked[:5])
        more = f" (+{len(focus.unranked) - 5} more)" if len(focus.unranked) > 5 else ""
        console.print(
            f"\n[dim]Not in the graph (deleted, excluded or unparseable): {shown}{more}[/dim]"
        )

    if focus.is_empty:
        console.print("[dim]Nothing in this diff is an in-project Python module.[/dim]")
