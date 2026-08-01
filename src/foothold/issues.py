"""Good-first-issue candidates, derived deterministically.

Three sources, all offline: TODO/FIXME markers, public functions without a
docstring in low-centrality modules, and source files with no matching test.
Low centrality matters - a first issue should not sit on the critical path.
"""

from __future__ import annotations

from dataclasses import dataclass

from foothold.models import RepoMap


@dataclass
class IssueCandidate:
    title: str
    body: str
    labels: list[str]
    difficulty: str


def propose(repo: RepoMap, limit: int = 10) -> list[IssueCandidate]:
    out: list[IssueCandidate] = []
    rank_of = {s.path: i for i, s in enumerate(repo.scores)}
    peripheral = len(repo.scores) // 2

    for marker in repo.markers:
        if rank_of.get(marker.path, 0) < peripheral // 2:
            continue  # too central for a newcomer
        out.append(
            IssueCandidate(
                title=f"{marker.kind.title()}: {marker.text or marker.path}"[:80],
                body=(
                    f"`{marker.path}:{marker.lineno}` carries a {marker.kind} marker:\n\n"
                    f"> {marker.text}\n\n"
                    "Self-contained and off the critical path — a good first change."
                ),
                labels=["good first issue"],
                difficulty="small",
            )
        )

    for path in repo.untested[:limit]:
        out.append(
            IssueCandidate(
                title=f"Add tests for {path}",
                body=(
                    f"`{path}` has no test file referencing it. Adding coverage is a "
                    "low-risk way to learn the module."
                ),
                labels=["good first issue", "tests"],
                difficulty="small",
            )
        )

    for score in repo.scores[peripheral:]:
        module = repo.modules[score.module]
        if module.docstring is None and module.defines:
            out.append(
                IssueCandidate(
                    title=f"Document the public API of {score.path}",
                    body=(
                        f"`{score.path}` exports {', '.join(module.defines[:5])} with no "
                        "module docstring."
                    ),
                    labels=["good first issue", "documentation"],
                    difficulty="small",
                )
            )
    return out[:limit]
