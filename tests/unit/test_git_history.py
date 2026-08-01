from __future__ import annotations

import shutil
import subprocess
from types import SimpleNamespace

from foothold.analyze import analyze
from foothold.collectors.git_history import churn_by_path


def test_missing_git_metadata_returns_empty_churn(minirepo, tmp_path):
    isolated = tmp_path / "minirepo"
    shutil.copytree(minirepo, isolated)

    assert churn_by_path(isolated) == {}


def test_nonzero_git_log_returns_empty_churn(monkeypatch, tmp_path):
    def failed_run(*args, **kwargs):
        return SimpleNamespace(returncode=128, stdout="", stderr="not a repository")

    monkeypatch.setattr(subprocess, "run", failed_run)

    assert churn_by_path(tmp_path) == {}


def test_analysis_without_git_history_keeps_ranking(minirepo, tmp_path):
    isolated = tmp_path / "minirepo"
    shutil.copytree(minirepo, isolated)

    repo = analyze(isolated)

    assert repo.scores
    assert all(score.churn == 0.0 for score in repo.scores)
