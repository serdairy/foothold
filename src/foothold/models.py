"""Core data structures shared across collectors, graph and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Module:
    """A single source file resolved to a dotted module path."""

    path: str
    module: str
    loc: int
    is_test: bool
    is_package_init: bool
    defines: tuple[str, ...] = ()
    docstring: str | None = None


@dataclass
class Edge:
    """A directed import edge between two in-project modules."""

    src: str
    dst: str
    lineno: int


@dataclass
class Marker:
    """A TODO/FIXME/HACK comment left in the source."""

    path: str
    lineno: int
    kind: str
    text: str


@dataclass
class Score:
    """Ranking output for one module."""

    module: str
    path: str
    total: float
    centrality: float
    churn: float
    fan_in: int
    fan_out: int
    loc: int
    reasons: list[str] = field(default_factory=list)


@dataclass
class RepoMap:
    """Everything Foothold knows about a repository after the offline pass."""

    root: str
    modules: dict[str, Module]
    edges: list[Edge]
    scores: list[Score]
    entrypoints: list[str]
    markers: list[Marker]
    untested: list[str]
    cycles: list[list[str]]

    @property
    def loc_total(self) -> int:
        return sum(m.loc for m in self.modules.values())
