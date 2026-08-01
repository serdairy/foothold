"""Build the in-project import graph.

External imports are dropped on purpose: the question Foothold answers is
"which files in *this* repository hold it together", and third-party packages
add nodes without adding signal.
"""

from __future__ import annotations

import networkx as nx

from foothold.models import Edge, Module


def _longest_known_prefix(target: str, known: set[str]) -> str | None:
    """``pkg.mod.func`` imported from ``pkg.mod`` resolves to ``pkg.mod``."""
    parts = target.split(".")
    for cut in range(len(parts), 0, -1):
        candidate = ".".join(parts[:cut])
        if candidate in known:
            return candidate
    return None


def _resolve(target: str, known: set[str], root_alias: str | None) -> str | None:
    """Resolve an import target to an in-project module, or None if external.

    ``root_alias`` handles the common case of pointing Foothold at a package
    directory (``foothold map ./rich``) rather than the repository root: inside
    that tree ``from rich.console import X`` must resolve to the local
    ``console`` module. Only that one prefix is stripped - blanket suffix
    matching would map ``os.path`` onto a local ``path.py``.
    """
    direct = _longest_known_prefix(target, known)
    if direct is not None:
        return direct
    if root_alias and target.startswith(f"{root_alias}."):
        return _longest_known_prefix(target[len(root_alias) + 1 :], known)
    return None


def build_graph(
    modules: dict[str, Module], edges: list[Edge], root_alias: str | None = None
) -> nx.DiGraph:
    graph = nx.DiGraph()
    for name, module in modules.items():
        graph.add_node(name, path=module.path, loc=module.loc, is_test=module.is_test)
    known = set(modules)
    for edge in edges:
        dst = _resolve(edge.dst, known, root_alias)
        if dst is None or dst == edge.src or edge.src not in known:
            continue
        if graph.has_edge(edge.src, dst):
            graph[edge.src][dst]["weight"] += 1
        else:
            graph.add_edge(edge.src, dst, weight=1, lineno=edge.lineno)
    return graph


def find_entrypoints(graph: nx.DiGraph, modules: dict[str, Module]) -> list[str]:
    """Modules nothing else imports, excluding tests and empty ``__init__`` files."""
    out = [
        name
        for name in graph.nodes
        if graph.in_degree(name) == 0
        and not modules[name].is_test
        and not (modules[name].is_package_init and modules[name].loc < 5)
    ]
    return sorted(out, key=lambda n: (-modules[n].loc, n))


def find_cycles(graph: nx.DiGraph, limit: int = 10) -> list[list[str]]:
    """Import cycles - the places where a newcomer's mental model breaks first."""
    cycles: list[list[str]] = []
    for cycle in nx.simple_cycles(graph):
        cycles.append(sorted(cycle))
        if len(cycles) >= limit:
            break
    return cycles
