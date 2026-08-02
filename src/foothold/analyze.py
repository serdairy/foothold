"""Orchestrates the offline pass: collect -> graph -> rank -> RepoMap."""

from __future__ import annotations

from pathlib import Path

from foothold.cache import ParseCache
from foothold.collectors import churn_by_path, collect_markers, collect_modules
from foothold.config import Config
from foothold.graph import build_graph, find_cycles, find_entrypoints, rank
from foothold.models import Module, RepoMap, Score


def _untested(modules: dict[str, Module], scores: list[Score]) -> list[str]:
    """Source modules with no test file whose name references them."""
    blob = " ".join(m.path for m in modules.values() if m.is_test)
    out = []
    for score in scores[:50]:
        stem = Path(score.path).stem
        if stem not in blob:
            out.append(score.path)
    return out


def analyze(root: Path, config: Config | None = None, *, use_cache: bool = True) -> RepoMap:
    config = config or Config.load(root)
    cache = ParseCache(root, enabled=use_cache)
    cache.load()
    modules, edges = collect_modules(root, config.excludes, cache)
    cache.save()
    graph = build_graph(modules, edges, root_alias=root.name)
    churn = churn_by_path(root)
    scores = rank(graph, modules, churn, config.weights)
    source_paths = [m.path for m in modules.values() if not m.is_test]
    return RepoMap(
        root=str(root),
        modules=modules,
        edges=edges,
        scores=scores,
        entrypoints=find_entrypoints(graph, modules),
        markers=collect_markers(root, source_paths),
        untested=_untested(modules, scores),
        cycles=find_cycles(graph),
    )
