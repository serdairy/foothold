from pkg.core import heart


def test_heart() -> None:
    assert heart() == 42
