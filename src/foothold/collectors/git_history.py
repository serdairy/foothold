"""Churn signal derived from git history via subprocess.

Only ``git log`` is invoked, with an explicit argv list and no shell. A repo
without git, or a shallow clone, degrades to a zero churn signal rather than
failing the run.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path


def churn_by_path(root: Path, since: str = "18.months") -> dict[str, int]:
    """Return {relative path: number of commits touching it}."""
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "log",
                f"--since={since}",
                "--name-only",
                "--pretty=format:",
                "--no-merges",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}
    counts: Counter[str] = Counter()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.endswith(".py"):
            counts[line] += 1
    return dict(counts)
