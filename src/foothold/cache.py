"""Content-addressed cache for parsed files.

Parsing is 90% of a run: on django, 3.6s of a 4.0s analysis. Everything a parse
produces is a pure function of the file's bytes, so it can be keyed by their
hash and reused until the bytes change.

What is stored is deliberately path-independent — line count, public
definitions, docstring, raw import statements. Anything derived from the file's
location (its dotted module name, whether it is a test, how a relative import
resolves) is recomputed on every run. A file that moves therefore cannot carry
stale answers with it, which is the failure mode a naive path-keyed cache has.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Bump when the stored shape or the parser's output changes. Old entries are
# then ignored rather than misread, because the file name itself carries this.
CACHE_FORMAT = 1


@dataclass(frozen=True)
class RawImport:
    """An import statement as written, before the module name is known."""

    lineno: int
    level: int = 0
    module: str | None = None
    names: tuple[str, ...] = ()
    plain: bool = False  # `import x` rather than `from x import y`

    def to_json(self) -> dict[str, Any]:
        return {
            "l": self.lineno,
            "v": self.level,
            "m": self.module,
            "n": list(self.names),
            "p": self.plain,
        }

    @staticmethod
    def from_json(raw: dict[str, Any]) -> RawImport:
        return RawImport(
            lineno=int(raw["l"]),
            level=int(raw["v"]),
            module=raw["m"],
            names=tuple(raw["n"]),
            plain=bool(raw["p"]),
        )


@dataclass(frozen=True)
class ParsedFile:
    """Everything parsing yields that does not depend on where the file lives."""

    loc: int
    defines: tuple[str, ...]
    docstring: str | None
    imports: tuple[RawImport, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "loc": self.loc,
            "defines": list(self.defines),
            "doc": self.docstring,
            "imports": [i.to_json() for i in self.imports],
        }

    @staticmethod
    def from_json(raw: dict[str, Any]) -> ParsedFile:
        return ParsedFile(
            loc=int(raw["loc"]),
            defines=tuple(raw["defines"]),
            docstring=raw["doc"],
            imports=tuple(RawImport.from_json(i) for i in raw["imports"]),
        )


def digest(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def cache_root() -> Path:
    """XDG cache directory, overridable for tests and for CI."""
    override = os.environ.get("FOOTHOLD_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or "~/.cache"
    return Path(base).expanduser() / "foothold"


@dataclass
class ParseCache:
    """One JSON file per analysed repository, keyed by content hash.

    Disabled instances are valid and do nothing, so callers never branch on
    whether caching is on.
    """

    root: Path
    enabled: bool = True
    entries: dict[str, ParsedFile] = field(default_factory=dict)
    seen: set[str] = field(default_factory=set)
    hits: int = 0
    misses: int = 0
    _loaded_count: int = 0

    @property
    def path(self) -> Path:
        # The repository path identifies the file; the Python minor version is in
        # the name because ast output is only guaranteed stable within one.
        key = hashlib.sha256(str(self.root.resolve()).encode()).hexdigest()[:16]
        py = f"py{sys.version_info.major}{sys.version_info.minor}"
        return cache_root() / f"v{CACHE_FORMAT}" / f"{key}-{py}.json"

    def load(self) -> None:
        if not self.enabled:
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict) or raw.get("format") != CACHE_FORMAT:
            return
        try:
            self.entries = {k: ParsedFile.from_json(v) for k, v in raw["files"].items()}
        except (KeyError, TypeError, ValueError):
            self.entries = {}
        self._loaded_count = len(self.entries)

    def get(self, key: str) -> ParsedFile | None:
        if not self.enabled:
            return None
        found = self.entries.get(key)
        if found is None:
            self.misses += 1
            return None
        self.hits += 1
        self.seen.add(key)
        return found

    def put(self, key: str, parsed: ParsedFile) -> None:
        if not self.enabled:
            return
        self.entries[key] = parsed
        self.seen.add(key)

    def save(self) -> None:
        """Write atomically, keeping only what this run touched.

        Pruning matters: without it the file grows by one entry for every edit
        ever made to the repository.
        """
        if not self.enabled:
            return
        kept = {k: v for k, v in self.entries.items() if k in self.seen}
        if not kept and not self._loaded_count:
            return
        payload = {"format": CACHE_FORMAT, "files": {k: v.to_json() for k, v in kept.items()}}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            # A cache that cannot be written is a slow run, not a failed one.
            return


def clear() -> int:
    """Delete every cache file. Returns how many were removed."""
    root = cache_root()
    if not root.exists():
        return 0
    removed = 0
    for file in sorted(root.rglob("*.json")):
        try:
            file.unlink()
            removed += 1
        except OSError:
            continue
    return removed
