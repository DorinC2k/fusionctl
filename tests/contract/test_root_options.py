from typer.testing import CliRunner

from fusionctl.main import app

runner = CliRunner()


def test_default_verbosity_emits_no_runtime_log() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "fusionctl" in result.stdout
    assert "Logging:" not in result.stderr


def test_single_v_is_version_flag() -> None:
    result = runner.invoke(app, ["-v"])

    assert result.exit_code == 0
    assert "fusionctl" in result.stdout


def test_double_v_enables_diagnostic_logging(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FUSION_APP_DIR", str(tmp_path))

    result = runner.invoke(app, ["-vv", "auth", "status"])

    assert result.exit_code == 1
    assert "Logging: detailed" in result.stderr
    assert "Config override: <default>" in result.stderr


def test_triple_v_enables_maximum_logging(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FUSION_APP_DIR", str(tmp_path))

    result = runner.invoke(app, ["-vvv", "--no-cache", "auth", "status"])

    assert result.exit_code == 1
    assert "Logging: maximum" in result.stderr
    assert "Config override: <default>" in result.stderr
    assert "Cache mode: disabled" in result.stderr
