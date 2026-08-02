"""Regression tests for the ways a repository can misbehave or mislead."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from foothold.analyze import analyze
from foothold.cache import ParseCache
from foothold.collectors.git_history import changed_paths, churn_by_path
from foothold.focus import focus_on

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@e",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@e",
    "PATH": "/usr/bin:/bin:/usr/local/bin",
}


def _git(root: Path, *args: str, home: Path) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env={**GIT_ENV, "HOME": str(home)},
    )


@pytest.fixture
def nested_repo(minirepo, tmp_path):
    """A git repository whose Python package sits in a subdirectory."""
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    shutil.copytree(minirepo, root / "src" / "pkgroot")
    _git(root, "init", "-q", "-b", "main", home=tmp_path)
    _git(root, "add", "-A", home=tmp_path)
    _git(root, "commit", "-qm", "initial", home=tmp_path)
    return root


def test_a_symlink_out_of_the_repository_is_not_read(minirepo, tmp_path):
    """Otherwise an unrelated file's contents reach the map, the cache and a PR comment."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text('"""SECRET."""\nKEY = "sk-x"\n')
    root = tmp_path / "repo"
    shutil.copytree(minirepo, root)
    (root / "linked.py").symlink_to(outside / "secret.py")

    repo = analyze(root, use_cache=False)

    assert "linked" not in repo.modules
    assert all("SECRET" not in (m.docstring or "") for m in repo.modules.values())


def test_a_symlink_inside_the_repository_is_still_read(minirepo, tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(minirepo, root)
    (root / "alias.py").symlink_to(root / "main.py")

    repo = analyze(root, use_cache=False)

    assert "alias" in repo.modules


@pytest.mark.parametrize("ref", ["--output=/tmp/foothold-should-not-exist", "-p", "", "nope"])
def test_a_ref_that_is_really_an_option_is_refused(nested_repo, ref):
    """`git diff --output=...` writes a file wherever the caller points it."""
    assert changed_paths(nested_repo, ref) is None
    assert not Path("/tmp/foothold-should-not-exist").exists()


def test_churn_is_relative_to_the_analysed_directory(nested_repo, tmp_path):
    """Regression: analysing a subdirectory silently scored every file at zero churn."""
    target = nested_repo / "src" / "pkgroot" / "pkg" / "core.py"
    target.write_text("VALUE = 2\n")
    _git(nested_repo, "add", "-A", home=tmp_path)
    _git(nested_repo, "commit", "-qm", "edit core", home=tmp_path)

    churn = churn_by_path(nested_repo / "src" / "pkgroot")

    assert "pkg/core.py" in churn
    assert not any(key.startswith("src/") for key in churn)


def test_since_finds_changes_when_analysing_a_subdirectory(nested_repo):
    """The same path mismatch made --since report an empty diff."""
    package = nested_repo / "src" / "pkgroot"
    (package / "pkg" / "core.py").write_text("VALUE = 3\n")

    changed = changed_paths(package, "HEAD")
    focus = focus_on(analyze(package, use_cache=False), changed or set())

    assert changed == {"pkg/core.py"}
    assert [s.path for s in focus.changed] == ["pkg/core.py"]


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows has no POSIX permission bits; chmod only toggles the read-only flag.",
)
def test_the_cache_file_is_not_world_readable(minirepo, tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "repo"
    shutil.copytree(minirepo, root)

    analyze(root)
    mode = stat.S_IMODE(ParseCache(root).path.stat().st_mode)

    assert mode & (stat.S_IRGRP | stat.S_IROTH) == 0
