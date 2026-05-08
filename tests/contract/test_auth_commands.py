from typer.testing import CliRunner

from fusionctl.main import app

runner = CliRunner()


def test_auth_login_status_logout(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FUSION_APP_DIR", str(tmp_path))

    login_result = runner.invoke(app, ["auth", "login", "--token", "bm_sv=abc; JSESSIONID=def"])
    assert login_result.exit_code == 0
    assert "Authenticated" in login_result.stdout
    assert "abc" not in login_result.stdout

    status_result = runner.invoke(app, ["auth", "status"])
    assert status_result.exit_code == 0
    assert "Authenticated" in status_result.stdout

    logout_result = runner.invoke(app, ["auth", "logout"])
    assert logout_result.exit_code == 0
    assert "Session cleared" in logout_result.stdout


def test_status_without_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FUSION_APP_DIR", str(tmp_path))

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 1
    assert "Not authenticated" in result.stderr
