"""Command line interface."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console

from foothold import __version__
from foothold.analyze import analyze
from foothold.config import Config
from foothold.issues import propose
from foothold.narrator import NarratorError, narrate
from foothold.narrator.client import build_context, estimate_tokens
from foothold.render import render_architecture, render_map

app = typer.Typer(
    add_completion=False,
    help="Turn an unfamiliar repository into a reading path.",
    no_args_is_help=True,
)
console = Console()
err = Console(stderr=True)


def _version(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Foothold reads a repository the way a senior engineer does on day one."""


@app.command("map")
def map_cmd(
    path: Path = typer.Argument(Path("."), help="Repository root."),
    top: int = typer.Option(30, "--top", "-n", help="How many files to show."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Rank the files that hold the repository together. Offline, no API key."""
    repo = analyze(path.resolve())
    if not repo.modules:
        err.print("[red]No Python modules found.[/red] Foothold v0.1 is Python-only.")
        raise typer.Exit(1)
    if as_json:
        console.print_json(
            json.dumps(
                {
                    "root": repo.root,
                    "modules": len(repo.modules),
                    "loc": repo.loc_total,
                    "entrypoints": [repo.modules[n].path for n in repo.entrypoints],
                    "cycles": repo.cycles,
                    "scores": [asdict(s) for s in repo.scores[:top]],
                }
            )
        )
        return
    render_map(repo, top=top)


@app.command("docs")
def docs_cmd(
    path: Path = typer.Argument(Path("."), help="Repository root."),
    out: Path = typer.Option(Path("ARCHITECTURE.md"), "--out", "-o"),
    top: int = typer.Option(20, "--top", "-n"),
    narrate_flag: bool = typer.Option(False, "--narrate", help="Add model-written prose."),
    yes: bool = typer.Option(False, "--yes", help="Skip the spend confirmation."),
) -> None:
    """Write ARCHITECTURE.md. Deterministic unless --narrate is passed."""
    repo = analyze(path.resolve())
    narrative = None
    if narrate_flag:
        config = Config.load(path.resolve())
        tokens = estimate_tokens(build_context(repo, top=top))
        if not yes:
            typer.confirm(f"Send ~{tokens:,} tokens to {config.model}?", abort=True)
        try:
            narrative, usage = narrate(repo, model=config.model, top=top)
            err.print(
                f"[dim]{usage.prompt_tokens}+{usage.completion_tokens} tokens, "
                f"~${usage.cost_usd():.4f}[/dim]"
            )
        except NarratorError as exc:
            err.print(f"[yellow]{exc} Falling back to the deterministic document.[/yellow]")
    out.write_text(render_architecture(repo, top=top, narrative=narrative), encoding="utf-8")
    console.print(f"Wrote [bold]{out}[/bold]")


@app.command("explain")
def explain_cmd(
    path: Path = typer.Argument(Path("."), help="Repository root."),
    top: int = typer.Option(25, "--top", "-n"),
    yes: bool = typer.Option(False, "--yes"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the context, send nothing."),
) -> None:
    """Explain the repository in prose, grounded in the ranked map."""
    repo = analyze(path.resolve())
    config = Config.load(path.resolve())
    context = build_context(repo, top=top)
    if dry_run:
        console.print(context)
        return
    if not yes:
        typer.confirm(f"Send ~{estimate_tokens(context):,} tokens to {config.model}?", abort=True)
    try:
        text, usage = narrate(repo, model=config.model, top=top)
    except NarratorError as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(text)
    err.print(f"[dim]~${usage.cost_usd():.4f}[/dim]")


@app.command("issues")
def issues_cmd(
    path: Path = typer.Argument(Path("."), help="Repository root."),
    limit: int = typer.Option(10, "--max", "-n"),
    as_markdown: bool = typer.Option(False, "--markdown"),
) -> None:
    """Propose good-first-issue candidates. Offline, no API key."""
    repo = analyze(path.resolve())
    candidates = propose(repo, limit=limit)
    if not candidates:
        console.print("No candidates found.")
        return
    for candidate in candidates:
        if as_markdown:
            console.print(f"### {candidate.title}\n\n{candidate.body}\n")
        else:
            console.print(f"[bold]{candidate.title}[/bold]")
            console.print(f"  [dim]{candidate.labels} · {candidate.difficulty}[/dim]")


if __name__ == "__main__":
    app()
