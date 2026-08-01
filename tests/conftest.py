import socket
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def minirepo() -> Path:
    return FIXTURES / "minirepo"


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    """Unit tests must not open sockets. Marked e2e tests are exempt."""
    if request.node.get_closest_marker("e2e"):
        return

    def guard(*args, **kwargs):
        raise RuntimeError("network access is not allowed in unit tests")

    monkeypatch.setattr(socket.socket, "connect", guard)
