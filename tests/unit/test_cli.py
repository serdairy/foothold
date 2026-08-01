from typer.testing import CliRunner

from foothold.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


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
