"""Rank modules by how much of the system they explain.

score = w_c * pagerank + w_h * churn + w_f * fan_in + w_s * size

All four components are min-max normalised to [0, 1] over the repository, so a
score is comparable within a repo but not across repos. The weights live in
``Config.weights`` and are printable via ``foothold map --explain-scoring``:
a ranking a user cannot interrogate is a ranking a user cannot trust.
"""

from __future__ import annotations

import math

import networkx as nx

from foothold.config import Weights
from foothold.models import Module, Score


def pagerank(
    graph: nx.DiGraph, alpha: float = 0.85, iterations: int = 60, tol: float = 1.0e-8
) -> dict[str, float]:
    """Power-iteration PageRank in pure Python.

    ``networkx.pagerank`` pulls in scipy and numpy - roughly 100 MB of wheels for
    a CLI whose graphs have hundreds of nodes, not millions. Sixty iterations of
    a dict-based power method is exact enough for a ranking and keeps the install
    to three small dependencies.
    """
    nodes = list(graph.nodes)
    if not nodes:
        return {}
    n = len(nodes)
    rank_of = dict.fromkeys(nodes, 1.0 / n)
    out_weight = {
        u: sum(d.get("weight", 1) for _, _, d in graph.out_edges(u, data=True)) for u in nodes
    }
    dangling = [u for u in nodes if out_weight[u] == 0]

    for _ in range(iterations):
        previous = rank_of
        leaked = alpha * sum(previous[u] for u in dangling) / n
        rank_of = {u: (1.0 - alpha) / n + leaked for u in nodes}
        for u, v, data in graph.edges(data=True):
            if out_weight[u]:
                rank_of[v] += alpha * previous[u] * data.get("weight", 1) / out_weight[u]
        if sum(abs(rank_of[u] - previous[u]) for u in nodes) < tol * n:
            break
    return rank_of


def _normalise(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if math.isclose(lo, hi):
        return dict.fromkeys(values, 0.0)
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def rank(
    graph: nx.DiGraph,
    modules: dict[str, Module],
    churn: dict[str, int],
    weights: Weights,
) -> list[Score]:
    targets = [n for n in graph.nodes if not modules[n].is_test]
    if not targets:
        return []
    # Edges point importer -> imported, so PageRank on the graph as-built already
    # rewards "many things depend on me". Reversing it would rank the modules with
    # the most imports, which is the opposite of what a newcomer needs.
    scores_pr = pagerank(graph) if graph.number_of_edges() else {}

    raw_centrality = {n: float(scores_pr.get(n, 0.0)) for n in targets}
    raw_churn = {n: float(churn.get(modules[n].path, 0)) for n in targets}
    raw_fan_in = {n: float(graph.in_degree(n)) for n in targets}
    raw_size = {n: math.log1p(modules[n].loc) for n in targets}

    norm_c = _normalise(raw_centrality)
    norm_h = _normalise(raw_churn)
    norm_f = _normalise(raw_fan_in)
    norm_s = _normalise(raw_size)

    scores: list[Score] = []
    for name in targets:
        total = (
            weights.centrality * norm_c[name]
            + weights.churn * norm_h[name]
            + weights.fan_in * norm_f[name]
            + weights.size * norm_s[name]
        )
        reasons = []
        if norm_f[name] > 0.6:
            reasons.append(f"imported by {int(raw_fan_in[name])} modules")
        if norm_h[name] > 0.6:
            reasons.append(f"{int(raw_churn[name])} commits in 18 months")
        if norm_c[name] > 0.6:
            reasons.append("high transitive reach")
        if modules[name].loc > 400:
            reasons.append(f"{modules[name].loc} lines")
        scores.append(
            Score(
                module=name,
                path=modules[name].path,
                total=round(total, 4),
                centrality=round(norm_c[name], 4),
                churn=round(norm_h[name], 4),
                fan_in=int(raw_fan_in[name]),
                fan_out=int(graph.out_degree(name)),
                loc=modules[name].loc,
                reasons=reasons,
            )
        )
    scores.sort(key=lambda s: (-s.total, s.module))
    return scores
