"""Configuration loading and ranking weights."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib

    HAVE_TOML = True
else:  # pragma: no cover - exercised on 3.10 only
    try:
        import tomli as tomllib

        HAVE_TOML = True
    except ModuleNotFoundError:
        HAVE_TOML = False

DEFAULT_EXCLUDES = (
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "site-packages",
)


@dataclass(frozen=True)
class Weights:
    """Relative weight of each ranking signal. Must be documented, not magic."""

    centrality: float = 0.45
    churn: float = 0.30
    fan_in: float = 0.15
    size: float = 0.10


@dataclass(frozen=True)
class Config:
    excludes: tuple[str, ...] = DEFAULT_EXCLUDES
    weights: Weights = Weights()
    top: int = 30
    model: str = "gpt-4o-mini"
    max_input_tokens: int = 12_000

    @staticmethod
    def load(root: Path) -> Config:
        """Read .foothold.toml if present; fall back to defaults."""
        path = root / ".foothold.toml"
        if not path.exists() or not HAVE_TOML:
            return Config()
        with path.open("rb") as fh:
            raw = tomllib.load(fh).get("foothold", {})
        weights = Weights(**raw.get("weights", {}))
        return Config(
            excludes=tuple(raw.get("excludes", DEFAULT_EXCLUDES)),
            weights=weights,
            top=int(raw.get("top", 30)),
            model=str(raw.get("model", "gpt-4o-mini")),
            max_input_tokens=int(raw.get("max_input_tokens", 12_000)),
        )
