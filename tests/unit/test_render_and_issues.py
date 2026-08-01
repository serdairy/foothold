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
