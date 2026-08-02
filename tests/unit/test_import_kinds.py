"""An import that does not run at import time cannot close an import cycle."""

from __future__ import annotations

from foothold.analyze import analyze
from foothold.collectors.python_ast import extract

SOURCE = '''
"""Module docstring."""
from typing import TYPE_CHECKING

import runtime_module

if TYPE_CHECKING:
    import type_only_module

class Thing:
    import class_body_module

def later():
    import function_module

if __name__ == "__main__":
    import demo_module
'''


def _kinds(source: str) -> dict[str, str]:
    parsed = extract(source, "x.py")
    return {name: imp.kind for imp in parsed.imports for name in imp.names}


def test_each_import_is_classified_by_when_it_runs():
    kinds = _kinds(SOURCE)

    assert kinds["runtime_module"] == "runtime"
    assert kinds["type_only_module"] == "type"
    assert kinds["function_module"] == "deferred"
    assert kinds["demo_module"] == "deferred"


def test_a_class_body_runs_at_import_time():
    """Unlike a function body, so it stays runtime."""
    assert _kinds(SOURCE)["class_body_module"] == "runtime"


def _repo(tmp_path, files: dict[str, str]):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return analyze(tmp_path, use_cache=False)


def test_a_type_checking_import_does_not_make_a_cycle(tmp_path):
    """Regression: highway-env was reported to have ten cycles. It has none.

    Every one ran through `if TYPE_CHECKING:` or a function-local import, which
    is precisely how those projects broke their cycles on purpose.
    """
    repo = _repo(
        tmp_path,
        {
            "a.py": "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    import b\n",
            "b.py": "import a\n",
        },
    )

    assert repo.cycles == []


def test_a_main_guard_import_does_not_make_a_cycle(tmp_path):
    """Regression: rich was reported to have ten cycles, all demo blocks."""
    repo = _repo(
        tmp_path,
        {
            "a.py": 'if __name__ == "__main__":\n    import b\n',
            "b.py": "import a\n",
        },
    )

    assert repo.cycles == []


def test_a_real_cycle_is_still_reported(tmp_path):
    repo = _repo(tmp_path, {"a.py": "import b\n", "b.py": "import a\n"})

    assert repo.cycles == [["a", "b"]]
