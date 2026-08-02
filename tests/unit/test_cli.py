from typer.testing import CliRunner

from foothold import __version__
from foothold.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_map_runs_offline(minirepo):
    result = runner.invoke(app, ["map", str(minirepo), "--top", "5"])
    assert result.exit_code == 0
    assert "pkg/core.py" in result.stdout


def test_map_json(minirepo):
    result = runner.invoke(app, ["map", str(minirepo), "--json"])
    assert result.exit_code == 0
    assert '"scores"' in result.stdout


def test_explain_dry_run_makes_no_call(minirepo):
    result = runner.invoke(app, ["explain", str(minirepo), "--dry-run"])
    assert result.exit_code == 0
    assert "Ranked core modules" in result.stdout


def test_docs_writes_file(minirepo, tmp_path):
    out = tmp_path / "ARCHITECTURE.md"
    result = runner.invoke(app, ["docs", str(minirepo), "--out", str(out)])
    assert result.exit_code == 0
    assert out.read_text().startswith("# Architecture")


def test_docs_reports_a_bad_output_path_without_a_traceback(minirepo, tmp_path):
    """CI on Windows caught this: an unwritable --out produced a full stack trace."""
    out = tmp_path / "no-such-dir" / "ARCHITECTURE.md"
    result = runner.invoke(app, ["docs", str(minirepo), "--out", str(out)])
    assert result.exit_code == 1
    assert "Traceback" not in result.stdout
    assert not out.exists()


def test_map_since_reports_a_bad_ref_without_a_traceback(tmp_path, minirepo):
    import shutil

    root = tmp_path / "minirepo"
    shutil.copytree(minirepo, root)

    result = runner.invoke(app, ["map", str(root), "--since", "nope"])

    assert result.exit_code == 1
    assert "Cannot diff against" in result.output
    assert "Traceback" not in result.output


def test_cache_command_prints_the_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))

    result = runner.invoke(app, ["cache"])

    assert result.exit_code == 0
    assert "0 file(s)" in result.output


def test_cache_clear_removes_the_files(tmp_path, minirepo, monkeypatch):
    import shutil

    monkeypatch.setenv("FOOTHOLD_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "minirepo"
    shutil.copytree(minirepo, root)
    runner.invoke(app, ["map", str(root)])

    result = runner.invoke(app, ["cache", "--clear"])

    assert "Removed 1 cache file(s)" in result.output
