from foothold.analyze import analyze
from foothold.collectors.python_ast import collect_modules
from foothold.config import DEFAULT_EXCLUDES, Weights
from foothold.graph.build import build_graph
from foothold.graph.rank import rank


def test_core_outranks_leaf(minirepo):
    """pkg.core is imported twice and imports nothing: it must rank above main."""
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges)
    scores = rank(graph, modules, churn={}, weights=Weights())
    order = [s.module for s in scores]
    assert order.index("pkg.core") < order.index("main")


def test_ranking_is_deterministic(minirepo):
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges)
    first = [s.module for s in rank(graph, modules, {}, Weights())]
    second = [s.module for s in rank(graph, modules, {}, Weights())]
    assert first == second


def test_tests_are_excluded_from_ranking(minirepo):
    repo = analyze(minirepo)
    assert all("test" not in s.path for s in repo.scores)


def test_churn_shifts_the_ranking(minirepo):
    """A rarely-imported but heavily-edited file must climb: churn is real signal."""
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges)
    hot = {"main.py": 500}
    baseline = [s.module for s in rank(graph, modules, {}, Weights())]
    shifted = [s.module for s in rank(graph, modules, hot, Weights())]
    assert baseline != shifted
    assert shifted.index("main") < baseline.index("main")


def test_pagerank_ranks_dependencies_above_dependents(minirepo):
    """Guards the direction of the graph - reversing it silently inverts the tool."""
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges)
    from foothold.graph.rank import pagerank

    pr = pagerank(graph)
    assert pr["pkg.core"] > pr["main"]
