"""Parse Python sources into Module records and raw import edges.

Deliberately uses the stdlib ``ast`` module: no third-party parser, no network,
no execution of the analysed code. Foothold never imports the repository it is
reading.
"""

from __future__ import annotations

import ast
from pathlib import Path

from foothold.cache import ParseCache, ParsedFile, RawImport, digest
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


def _resolve_relative_raw(current: str, node: RawImport) -> str | None:
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


def extract(source: str, filename: str) -> ParsedFile:
    """Parse one file into facts that do not depend on where it lives.

    Kept separate from :func:`build_records` so the result can be cached by the
    hash of ``source`` alone.
    """
    tree = ast.parse(source, filename=filename)
    imports: list[RawImport] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.append(
                RawImport(
                    lineno=node.lineno,
                    names=tuple(alias.name for alias in node.names),
                    plain=True,
                )
            )
        elif isinstance(node, ast.ImportFrom):
            imports.append(
                RawImport(
                    lineno=node.lineno,
                    level=node.level,
                    module=node.module,
                    names=tuple(alias.name for alias in node.names),
                )
            )
    return ParsedFile(
        loc=source.count("\n") + 1,
        defines=_public_defs(tree),
        docstring=ast.get_docstring(tree),
        imports=tuple(imports),
    )


def build_records(rel: str, parsed: ParsedFile) -> tuple[Module, list[Edge]]:
    """Apply everything that depends on the file's path to a parsed file."""
    mod = module_name(rel)
    edges: list[Edge] = []
    for imp in parsed.imports:
        if imp.plain:
            edges.extend(Edge(mod, name, imp.lineno) for name in imp.names)
            continue
        target = _resolve_relative_raw(mod, imp)
        if target is None:
            continue
        if target:
            edges.append(Edge(mod, target, imp.lineno))
            edges.extend(Edge(mod, f"{target}.{name}", imp.lineno) for name in imp.names)
        else:
            # ``from . import x`` anchored at the repository root
            edges.extend(Edge(mod, name, imp.lineno) for name in imp.names)
    module = Module(
        path=rel,
        module=mod,
        loc=parsed.loc,
        is_test=_is_test(rel),
        is_package_init=Path(rel).name == "__init__.py",
        defines=parsed.defines,
        docstring=parsed.docstring,
    )
    return module, edges


def parse_file(root: Path, rel: str) -> tuple[Module, list[Edge]]:
    source = (root / rel).read_text(encoding="utf-8", errors="replace")
    return build_records(rel, extract(source, rel))


def collect_modules(
    root: Path,
    excludes: tuple[str, ...],
    cache: ParseCache | None = None,
) -> tuple[dict[str, Module], list[Edge]]:
    """Walk the tree once, returning modules keyed by dotted name and raw edges."""
    cache = cache or ParseCache(root, enabled=False)
    modules: dict[str, Module] = {}
    edges: list[Edge] = []
    resolved_root = root.resolve()
    for file in sorted(root.rglob("*.py")):
        rel = file.relative_to(root).as_posix()
        if any(part in excludes for part in Path(rel).parts):
            continue
        # A symlink pointing outside the repository is not part of the repository.
        # Following one would put the contents of an unrelated file into the map,
        # the cache, ARCHITECTURE.md and — with the action's `comment` input — a
        # public pull request comment.
        try:
            if not file.resolve().is_relative_to(resolved_root):
                continue
            raw = file.read_bytes()
        except (OSError, RuntimeError):
            continue
        key = digest(raw)
        parsed = cache.get(key)
        if parsed is None:
            try:
                parsed = extract(raw.decode("utf-8", errors="replace"), rel)
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            cache.put(key, parsed)
        module, file_edges = build_records(rel, parsed)
        if not module.module:
            continue
        modules[module.module] = module
        edges.extend(file_edges)
    return modules, edges
