"""Helpers."""
from pkg.core import heart


def shout(text: str) -> str:
    return f"{text}!{heart()}"
