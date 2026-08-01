"""The only component that talks to a model.

Design constraints, in order of importance:

1. The model receives a *pruned* context - the ranked file list and selected
   docstrings - never the repository. Cost scales with the summary, not the code.
2. Every call reports its estimated spend before it happens; non-interactive
   runs must pass ``--yes``.
3. The dependency is optional. Without ``pip install foothold[narrate]``
   every other command still works.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from foothold.models import RepoMap

SYSTEM = (
    "You are documenting an unfamiliar codebase for a new contributor. You are given a "
    "ranked file list produced by static analysis, not the source. Describe what the "
    "system does and in what order to read it. State only what the data supports; if a "
    "module's purpose is unclear from its name and docstring, say so."
)


class NarratorError(RuntimeError):
    """Raised when narration is requested but unavailable."""


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int

    def cost_usd(self, per_m_in: float = 0.15, per_m_out: float = 0.60) -> float:
        return (self.prompt_tokens * per_m_in + self.completion_tokens * per_m_out) / 1e6


def build_context(repo: RepoMap, top: int = 25) -> str:
    """Assemble the pruned context. Kept pure so it can be snapshot-tested."""
    lines = [f"Repository: {repo.root}", f"{len(repo.modules)} modules, {repo.loc_total} lines", ""]
    lines.append("Entry points:")
    lines += [f"- {repo.modules[n].path}" for n in repo.entrypoints[:6]]
    lines.append("")
    lines.append("Ranked core modules (score, imported-by, lines, docstring first line):")
    for score in repo.scores[:top]:
        doc = (repo.modules[score.module].docstring or "").strip().splitlines()
        lines.append(
            f"- {score.path} | {score.total:.3f} | in={score.fan_in} | loc={score.loc} | "
            f"{doc[0] if doc else ''}"
        )
    if repo.cycles:
        lines += ["", "Import cycles:"] + [f"- {' -> '.join(c)}" for c in repo.cycles[:5]]
    return "\n".join(lines)


def estimate_tokens(context: str) -> int:
    """Deliberately crude: 4 chars/token. Over-estimates, which is the safe direction."""
    return len(context) // 4 + 400


def narrate(repo: RepoMap, model: str, top: int = 25) -> tuple[str, Usage]:
    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise NarratorError(
            "Narration needs the optional dependency: pip install 'foothold[narrate]'"
        ) from exc
    if not os.getenv("OPENAI_API_KEY"):
        raise NarratorError("OPENAI_API_KEY is not set.")

    context = build_context(repo, top=top)
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": context}],
        temperature=0.2,
    )
    usage = Usage(
        prompt_tokens=getattr(response.usage, "prompt_tokens", 0),
        completion_tokens=getattr(response.usage, "completion_tokens", 0),
    )
    return response.choices[0].message.content or "", usage
