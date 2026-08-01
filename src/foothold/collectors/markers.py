"""Extract TODO/FIXME/HACK/XXX markers - raw material for issue candidates."""

from __future__ import annotations

import re
from pathlib import Path

from foothold.models import Marker

PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)", re.IGNORECASE)


def collect_markers(root: Path, paths: list[str]) -> list[Marker]:
    markers: list[Marker] = []
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = PATTERN.search(line)
            if match:
                markers.append(
                    Marker(
                        path=rel,
                        lineno=lineno,
                        kind=match.group(1).upper(),
                        text=match.group(2).strip()[:160],
                    )
                )
    return markers
