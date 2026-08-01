"""API layer."""
from pkg.core import heart
from pkg.util.helpers import shout


def endpoint() -> str:
    # TODO: add pagination
    return shout(str(heart()))
