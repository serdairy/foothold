"""Foothold: turn an unfamiliar repository into a reading path."""

from importlib.metadata import version

# Single source of truth. The version is read from package metadata so it cannot
# drift from pyproject.toml, which is exactly what happened in v0.1.1.
__version__ = version("foothold")
