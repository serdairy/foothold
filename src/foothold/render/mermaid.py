"""Mermaid diagram of the top-N subgraph - GitHub renders it natively."""

from __future__ import annotations

from foothold.models import RepoMap


def _slug(name: str) -> str:
    return name.replace(".", "_").replace("-", "_")


def render_mermaid(repo: RepoMap, top: int = 12) -> str:
    keep = {s.module for s in repo.scores[:top]}
    lines = ["```mermaid", "graph LR"]
    for score in repo.scores[:top]:
        lines.append(f'    {_slug(score.module)}["{score.path}"]')
    seen: set[tuple[str, str]] = set()
    for edge in repo.edges:
        src, dst = edge.src, edge.dst
        if src in keep and dst in keep and (src, dst) not in seen and src != dst:
            seen.add((src, dst))
            lines.append(f"    {_slug(src)} --> {_slug(dst)}")
    lines.append("```")
    return "\n".join(lines)
