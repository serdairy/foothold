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
    statements: int = 0

    @property
    def is_namespace_only(self) -> bool:
        """A package marker with no code in it.

        An empty ``__init__.py`` still carries transitive import weight, which is
        how a zero-line file reached the top of codecarbon's map. It is a routing
        node, not something a newcomer should be told to read.

        A package marker holding only a docstring is kept: one sentence saying
        what the package is for is exactly what someone arriving wants.
        """
        return self.is_package_init and self.statements == 0 and not self.docstring


@dataclass
class Edge:
    """A directed import edge between two in-project modules.

    ``kind`` separates an import that runs when the module is imported from one
    that does not. ``if TYPE_CHECKING:`` blocks and imports inside a function are
    exactly how Python projects break a cycle on purpose; counting them as
    ordinary edges reports the fix as the problem.
    """

    src: str
    dst: str
    lineno: int
    kind: str = "runtime"


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
