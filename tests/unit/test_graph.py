"""The graph for tests/fixtures/minirepo is known by hand; assert against it."""

import networkx as nx

from foothold.collectors.python_ast import collect_modules, module_name
from foothold.config import DEFAULT_EXCLUDES
from foothold.graph.build import build_graph, find_cycles, find_entrypoints


def test_module_name_strips_src_and_init():
    assert module_name("src/pkg/mod.py") == "pkg.mod"
    assert module_name("pkg/__init__.py") == "pkg"
    assert module_name("main.py") == "main"


def test_graph_matches_hand_written_expectation(minirepo):
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges)

    assert set(modules) >= {"main", "pkg", "pkg.api", "pkg.core", "pkg.util.helpers"}
    assert graph.has_edge("main", "pkg.api")
    assert graph.has_edge("pkg.api", "pkg.core")
    assert graph.has_edge("pkg.api", "pkg.util.helpers")
    assert graph.has_edge("pkg.util.helpers", "pkg.core")
    # core is a sink: it imports nothing in-project
    assert graph.out_degree("pkg.core") == 0
    # third-party and stdlib imports must not become nodes
    assert "socket" not in graph.nodes


def test_entrypoint_is_main(minirepo):
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges)
    assert "main" in find_entrypoints(graph, modules)
    assert "pkg.core" not in find_entrypoints(graph, modules)


def test_no_cycles_in_fixture(minirepo):
    modules, edges = collect_modules(minirepo, DEFAULT_EXCLUDES)
    assert find_cycles(build_graph(modules, edges)) == []


def test_cycle_detection_on_synthetic_graph():
    graph = nx.DiGraph()
    graph.add_edges_from([("a", "b"), ("b", "a")])
    assert find_cycles(graph) == [["a", "b"]]


def test_root_alias_resolves_absolute_self_imports(tmp_path):
    """`foothold map ./mypkg` must still link `from mypkg.a import x` to a.py."""
    (tmp_path / "mypkg").mkdir()
    (tmp_path / "mypkg" / "a.py").write_text("def x():\n    return 1\n")
    (tmp_path / "mypkg" / "b.py").write_text("from mypkg.a import x\n")
    modules, edges = collect_modules(tmp_path / "mypkg", DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges, root_alias="mypkg")
    assert graph.has_edge("b", "a")


def test_root_alias_does_not_swallow_stdlib(tmp_path):
    """Stripping the alias must not turn `os.path` into a local `path` module."""
    (tmp_path / "os").mkdir()
    (tmp_path / "os" / "path.py").write_text("VALUE = 1\n")
    (tmp_path / "os" / "user.py").write_text("import json\nimport os.path\n")
    modules, edges = collect_modules(tmp_path / "os", DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges, root_alias="os")
    assert "json" not in graph.nodes


def test_relative_import_from_toplevel_module(tmp_path):
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    (tmp_path / "b.py").write_text("from . import a\n")
    modules, edges = collect_modules(tmp_path, DEFAULT_EXCLUDES)
    graph = build_graph(modules, edges, root_alias=tmp_path.name)
    assert graph.has_edge("b", "a")


def test_cycles_are_the_same_whatever_order_the_graph_was_built_in():
    """Regression: simple_cycles yields in set-iteration order, so a regenerated
    ARCHITECTURE.md listed different cycles on every process."""
    import networkx as nx

    from foothold.graph.build import find_cycles

    forward = nx.DiGraph()
    forward.add_edges_from([("a", "b"), ("b", "a"), ("c", "d"), ("d", "c"), ("b", "c")])
    backward = nx.DiGraph()
    backward.add_edges_from([("d", "c"), ("c", "d"), ("b", "a"), ("a", "b"), ("b", "c")])

    assert find_cycles(forward) == find_cycles(backward)


def test_a_reported_cycle_is_a_real_chain_of_imports():
    """Regression: the nodes used to be sorted alphabetically and printed with
    arrows between them, so most arrows claimed an import that did not exist."""
    import networkx as nx

    from foothold.graph.build import find_cycles

    graph = nx.DiGraph()
    graph.add_edges_from([("zebra", "apple"), ("apple", "moose"), ("moose", "zebra")])

    (cycle,) = find_cycles(graph)

    assert cycle[0] == "apple"  # rotated to the smallest node, direction intact
    for src, dst in zip(cycle, [*cycle[1:], cycle[0]], strict=True):
        assert graph.has_edge(src, dst)


def test_shorter_cycles_come_first():
    import networkx as nx

    from foothold.graph.build import find_cycles

    graph = nx.DiGraph()
    graph.add_edges_from([("a", "b"), ("b", "a"), ("c", "d"), ("d", "e"), ("e", "c")])

    lengths = [len(c) for c in find_cycles(graph)]

    assert lengths == sorted(lengths)
