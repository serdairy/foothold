"""Parse Python sources into Module records and raw import edges.

Deliberately uses the stdlib ``ast`` module: no third-party parser, no network,
no execution of the analysed code. Foothold never imports the repository it is
reading.
"""

from __future__ import annotations

import ast
from pathlib import Path

from foothold.models import Edge, Module

TEST_HINTS = ("tests/", "test_", "_test.py", "conftest.py")


def _is_test(rel: str) -> bool:
    name = Path(rel).name
    return (
        rel.startswith("tests/")
        or "/tests/" in rel
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def module_name(rel: str) -> str:
    """Map ``src/pkg/mod.py`` -> ``pkg.mod`` and ``pkg/__init__.py`` -> ``pkg``."""
    parts = list(Path(rel).with_suffix("").parts)
    if parts and parts[0] in {"src", "lib"}:
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _public_defs(tree: ast.Module) -> tuple[str, ...]:
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and (
            not node.name.startswith("_")
        ):
            out.append(node.name)
    return tuple(out)


def _resolve_relative(current: str, node: ast.ImportFrom) -> str | None:
    """Turn ``from ..graph import build`` inside ``a.b.c`` into ``a.graph.build``."""
    if node.level == 0:
        return node.module
    base = current.split(".")
    anchor = base[: len(base) - node.level + 1] if node.level > 1 else base
    prefix = ".".join(anchor[:-1] if node.level == 1 else anchor)
    if not prefix:
        # ``from . import x`` inside a top-level module: the anchor is the root
        return node.module or ""
    return f"{prefix}.{node.module}" if node.module else prefix


def parse_file(root: Path, rel: str) -> tuple[Module, list[Edge]]:
    source = (root / rel).read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=rel)
    mod = module_name(rel)
    edges: list[Edge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            edges.extend(Edge(mod, alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_relative(mod, node)
            if target is None:
                continue
            if target:
                edges.append(Edge(mod, target, node.lineno))
                edges.extend(Edge(mod, f"{target}.{a.name}", node.lineno) for a in node.names)
            else:
                # ``from . import x`` anchored at the repository root
                edges.extend(Edge(mod, a.name, node.lineno) for a in node.names)
    module = Module(
        path=rel,
        module=mod,
        loc=source.count("\n") + 1,
        is_test=_is_test(rel),
        is_package_init=Path(rel).name == "__init__.py",
        defines=_public_defs(tree),
        docstring=ast.get_docstring(tree),
    )
    return module, edges


def collect_modules(root: Path, excludes: tuple[str, ...]) -> tuple[dict[str, Module], list[Edge]]:
    """Walk the tree once, returning modules keyed by dotted name and raw edges."""
    modules: dict[str, Module] = {}
    edges: list[Edge] = []
    for file in sorted(root.rglob("*.py")):
        rel = file.relative_to(root).as_posix()
        if any(part in excludes for part in Path(rel).parts):
            continue
        try:
            module, file_edges = parse_file(root, rel)
        except (SyntaxError, UnicodeDecodeError, ValueError):
            continue
        if not module.module:
            continue
        modules[module.module] = module
        edges.extend(file_edges)
    return modules, edges
