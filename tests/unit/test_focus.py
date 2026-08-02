from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from foothold.analyze import analyze
from foothold.collectors.git_history import changed_paths
from foothold.focus import focus_on


@pytest.fixture
def git_repo(minirepo, tmp_path):
    root = tmp_path / "minirepo"
    shutil.copytree(minirepo, root)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            env={
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@e",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@e",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(tmp_path),
            },
        )

    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-qm", "initial")
    return root


def test_changed_paths_lists_only_edited_python_files(git_repo):
    (git_repo / "pkg" / "core.py").write_text("VALUE = 2\n")
    (git_repo / "notes.txt").write_text("ignored\n")

    assert changed_paths(git_repo, "HEAD") == {"pkg/core.py"}


def test_changed_paths_reports_a_bad_ref_as_none(git_repo):
    assert changed_paths(git_repo, "no-such-ref") is None


def test_an_unchanged_tree_is_an_empty_set_not_none(git_repo):
    """Empty means nothing changed; None means git could not answer. Not the same."""
    assert changed_paths(git_repo, "HEAD") == set()


def test_focus_finds_what_imports_the_changed_file(minirepo):
    repo = analyze(minirepo, use_cache=False)

    focus = focus_on(repo, {"pkg/core.py"})

    assert [s.path for s in focus.changed] == ["pkg/core.py"]
    dependents = {s.path for s in focus.dependents}
    assert "pkg/api.py" in dependents
    assert "pkg/core.py" not in dependents


def test_changed_tests_are_named_rather_than_called_unranked(minirepo):
    repo = analyze(minirepo, use_cache=False)

    focus = focus_on(repo, {"tests/test_core.py"})

    assert focus.changed_tests == ["tests/test_core.py"]
    assert focus.unranked == []


def test_a_deleted_file_is_reported_as_unranked(minirepo):
    repo = analyze(minirepo, use_cache=False)

    focus = focus_on(repo, {"pkg/gone.py"})

    assert focus.unranked == ["pkg/gone.py"]
    assert focus.is_empty


def test_changed_files_are_ordered_by_weight_not_by_path(minirepo):
    repo = analyze(minirepo, use_cache=False)

    focus = focus_on(repo, {"pkg/core.py", "pkg/api.py", "main.py"})
    totals = [s.total for s in focus.changed]

    assert totals == sorted(totals, reverse=True)
    assert len(focus.changed) == 3


def test_focus_uses_the_repository_root_alias(tmp_path, minirepo):
    """Regression: absolute self-imports only resolve when the root name is stripped."""
    root = tmp_path / "minirepo"
    shutil.copytree(minirepo, root)
    repo = analyze(root, use_cache=False)

    focus = focus_on(repo, {"pkg/core.py"})

    assert Path(repo.root).name == "minirepo"
    assert focus.dependents
