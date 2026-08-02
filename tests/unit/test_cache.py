from __future__ import annotations

import shutil

from foothold.analyze import analyze
from foothold.cache import CACHE_FORMAT, ParseCache, digest
from foothold.collectors.python_ast import collect_modules


def _repo(minirepo, tmp_path):
    isolated = tmp_path / "minirepo"
    shutil.copytree(minirepo, isolated)
    return isolated


def test_second_run_reads_every_file_from_cache(minirepo, tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = _repo(minirepo, tmp_path)

    cold = ParseCache(root)
    cold.load()
    collect_modules(root, (), cold)
    cold.save()

    warm = ParseCache(root)
    warm.load()
    collect_modules(root, (), warm)

    assert cold.hits == 0
    assert cold.misses > 0
    assert warm.misses == 0
    assert warm.hits == cold.misses


def test_editing_a_file_invalidates_only_that_entry(minirepo, tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = _repo(minirepo, tmp_path)

    first = ParseCache(root)
    first.load()
    collect_modules(root, (), first)
    first.save()

    (root / "pkg" / "core.py").write_text("import os\n\n\ndef added() -> None:\n    pass\n")

    second = ParseCache(root)
    second.load()
    modules, _ = collect_modules(root, (), second)
    second.save()

    assert second.misses == 1
    assert second.hits == first.misses - 1
    assert "added" in modules["pkg.core"].defines


def test_a_cache_from_another_format_is_ignored(minirepo, tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = _repo(minirepo, tmp_path)

    warm = ParseCache(root)
    warm.load()
    collect_modules(root, (), warm)
    warm.save()

    stale = warm.path.read_text().replace(f'"format":{CACHE_FORMAT}', '"format":999')
    warm.path.write_text(stale)

    reloaded = ParseCache(root)
    reloaded.load()

    assert reloaded.entries == {}


def test_a_corrupt_cache_file_does_not_break_the_run(minirepo, tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = _repo(minirepo, tmp_path)

    cache = ParseCache(root)
    cache.path.parent.mkdir(parents=True, exist_ok=True)
    cache.path.write_text("{not json at all")
    cache.load()

    modules, _ = collect_modules(root, (), cache)

    assert modules


def test_disabled_cache_writes_nothing(minirepo, tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(cache_dir))
    root = _repo(minirepo, tmp_path)

    analyze(root, use_cache=False)

    assert not cache_dir.exists()


def test_the_cache_does_not_grow_with_every_edit(minirepo, tmp_path, monkeypatch):
    """Entries not seen during a run are pruned, so the file tracks the repo size."""
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = _repo(minirepo, tmp_path)
    target = root / "pkg" / "core.py"

    for i in range(5):
        target.write_text(f"VALUE = {i}\n")
        analyze(root)

    cache = ParseCache(root)
    cache.load()

    assert len(cache.entries) == len(list(root.rglob("*.py")))


def test_the_same_bytes_hash_the_same_regardless_of_path():
    assert digest(b"x = 1\n") == digest(b"x = 1\n")
    assert digest(b"x = 1\n") != digest(b"x = 2\n")
