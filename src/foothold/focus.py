"""Narrow a repository map to what a diff touched, and to what depends on it.

The ranked map answers "where is the centre of this project". On a pull request
the useful question is different: "what did this change, and what else now has
to be read because of it". Both are the same graph, walked from different
starting points.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from foothold.graph import build_graph
from foothold.models import RepoMap, Score


@dataclass(frozen=True)
class Focus:
    """A diff, resolved against the import graph."""

    changed: list[Score]
    dependents: list[Score]
    changed_tests: list[str]
    unranked: list[str]

    @property
    def is_empty(self) -> bool:
        return not self.changed and not self.dependents and not self.changed_tests


def focus_on(repo: RepoMap, changed_files: set[str]) -> Focus:
    """Split a set of changed paths into ranked files, tests and everything else."""
    by_path = {score.path: score for score in repo.scores}
    module_by_path = {m.path: name for name, m in repo.modules.items()}
    # Ranking deliberately excludes tests, so a changed test file has no score.
    # Reporting it as "unranked" alongside deleted files would be misleading.
    test_paths = {m.path for m in repo.modules.values() if m.is_test}

    changed_scores = sorted(
        (by_path[p] for p in changed_files if p in by_path),
        key=lambda s: (-s.total, s.path),
    )
    changed_tests = sorted(p for p in changed_files if p in test_paths)
    accounted = {s.path for s in changed_scores} | set(changed_tests)
    unranked = sorted(p for p in changed_files if p not in accounted)

    graph = build_graph(repo.modules, repo.edges, root_alias=Path(repo.root).name)
    changed_modules = {module_by_path[p] for p in changed_files if p in module_by_path}

    dependent_modules: set[str] = set()
    for name in changed_modules:
        if graph.has_node(name):
            dependent_modules.update(graph.predecessors(name))
    dependent_modules -= changed_modules

    by_module = {score.module: score for score in repo.scores}
    dependents = sorted(
        (by_module[m] for m in dependent_modules if m in by_module),
        key=lambda s: (-s.total, s.path),
    )
    return Focus(
        changed=changed_scores,
        dependents=dependents,
        changed_tests=changed_tests,
        unranked=unranked,
    )
