"""Git-derived signals: churn, and the set of files a diff touched.

Only ``git log`` and ``git diff`` are invoked, with an explicit argv list and no
shell. A repository without git, or a shallow clone, degrades to a zero churn
signal rather than failing the run.

Both commands are given ``--relative`` so that paths come back relative to the
directory being analysed. Without it, analysing a subdirectory of a repository
returns repository-root paths that match nothing, and the churn term silently
collapses to zero for every file — 30% of the ranking weight, gone, with no
error. That was real: on django, analysing ``django/`` scored 906 files with
churn on none of them.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

TIMEOUT_SECONDS = 60


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc


def churn_by_path(root: Path, since: str = "18.months") -> dict[str, int]:
    """Return {path relative to root: number of commits touching it}."""
    proc = _git(
        root,
        "log",
        f"--since={since}",
        "--name-only",
        "--pretty=format:",
        "--no-merges",
        "--relative",
    )
    if proc is None or proc.returncode != 0:
        return {}
    counts: Counter[str] = Counter()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.endswith(".py"):
            counts[line] += 1
    return dict(counts)


def changed_paths(root: Path, ref: str) -> set[str] | None:
    """Return Python files that differ from ``ref``, or None if ref is unusable.

    None and the empty set mean different things: the first is "I could not ask
    git", the second is "nothing changed". Callers must not conflate them.
    """
    # A ref starting with a dash is parsed by git as an option, not a revision.
    # `--since=--output=/tmp/x` made `git diff` write a file at a path of the
    # caller's choosing. argv is explicit so there is no shell involved, but
    # option injection is enough on its own.
    if not ref or ref.startswith("-"):
        return None
    verify = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if verify is None or verify.returncode != 0:
        return None
    proc = _git(root, "diff", "--name-only", "--relative", ref, "--")
    if proc is None or proc.returncode != 0:
        return None
    return {line.strip() for line in proc.stdout.splitlines() if line.strip().endswith(".py")}
