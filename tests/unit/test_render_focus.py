from __future__ import annotations

import io

from rich.console import Console

from foothold.analyze import analyze
from foothold.focus import focus_on
from foothold.render import render_focus, render_map


def _render(repo, focus, top=10) -> str:
    buffer = io.StringIO()
    render_focus(repo, focus, top=top, console=Console(file=buffer, width=120))
    return buffer.getvalue()


def test_focus_output_names_the_change_and_what_reads_it(minirepo):
    repo = analyze(minirepo, use_cache=False)

    out = _render(repo, focus_on(repo, {"pkg/core.py"}))

    assert "1 changed source file" in out
    assert "pkg/core.py" in out
    assert "Read next: these import what changed" in out
    assert "pkg/api.py" in out


def test_a_touched_test_is_labelled_as_a_test(minirepo):
    repo = analyze(minirepo, use_cache=False)

    out = _render(repo, focus_on(repo, {"tests/test_core.py"}))

    assert "Tests touched" in out
    assert "Not in the graph" not in out


def test_a_diff_with_no_python_says_so_plainly(minirepo):
    repo = analyze(minirepo, use_cache=False)

    out = _render(repo, focus_on(repo, {"README.md"}))

    assert "Nothing in this diff is an in-project Python module." in out


def test_full_map_still_renders(minirepo):
    repo = analyze(minirepo, use_cache=False)
    buffer = io.StringIO()

    render_map(repo, top=5, console=Console(file=buffer, width=120))
    out = buffer.getvalue()

    assert "modules" in out
    assert "pkg/core.py" in out
