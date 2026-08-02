from foothold.analyze import analyze
from foothold.issues import propose
from foothold.narrator.client import build_context, estimate_tokens
from foothold.render import render_architecture, render_mermaid


def test_architecture_document_is_self_contained(minirepo):
    doc = render_architecture(analyze(minirepo))
    assert doc.startswith("# Architecture")
    assert "```mermaid" in doc
    assert "pkg/core.py" in doc
    assert "How this file is scored" in doc


def test_architecture_is_stable_across_runs(minirepo):
    assert render_architecture(analyze(minirepo)) == render_architecture(analyze(minirepo))


def test_mermaid_only_contains_ranked_nodes(minirepo):
    repo = analyze(minirepo)
    diagram = render_mermaid(repo, top=2)
    assert diagram.count("-->") <= 2


def test_issue_candidates_pick_up_the_todo(minirepo):
    titles = " ".join(c.title for c in propose(analyze(minirepo), limit=20))
    assert "pagination" in titles.lower() or "todo" in titles.lower()


def test_context_is_bounded_and_excludes_source(minirepo):
    repo = analyze(minirepo)
    context = build_context(repo)
    assert "def heart" not in context  # source code never leaves the machine
    assert estimate_tokens(context) < 4_000


def test_where_to_start_lists_the_ranking_not_the_entry_points(minirepo):
    """Regression: on highway-env this section recommended benchmark scripts.

    Entry points are modules nothing imports, which on a real repository means
    scripts and examples. Useful, but not an answer to "where do I start".
    """
    repo = analyze(minirepo, use_cache=False)
    doc = render_architecture(repo)
    start = doc.split("## Where to start")[1].split("##")[0].strip().splitlines()

    assert start[0].startswith(f"1. `{repo.scores[0].path}`")
    assert start[0].startswith("1. `pkg/core.py`")
    assert len(start) == 5


def test_entry_points_are_kept_under_their_own_heading(minirepo):
    doc = render_architecture(analyze(minirepo, use_cache=False))

    assert "## Entry points" in doc
    assert "main.py" in doc.split("## Entry points")[1].split("##")[0]


def test_documentation_config_is_not_ranked(tmp_path, minirepo):
    """Sphinx's conf.py ranked 14th of 66 on highway-env. It is not source."""
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(minirepo, root)
    (root / "docs").mkdir()
    (root / "docs" / "conf.py").write_text("project = 'x'\nimport pkg.core\n")

    repo = analyze(root, use_cache=False)

    assert all("docs/conf.py" not in s.path for s in repo.scores)
