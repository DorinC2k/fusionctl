from fusionctl.services.auth_service import AuthService


def test_login_status_and_logout(auth_service: AuthService) -> None:
    session = auth_service.login_with_cookie("bm_sv=abc; JSESSIONID=def")

    assert session.is_valid
    is_valid, stored = auth_service.status()
    assert is_valid is True
    assert stored is not None
    assert stored.token == "bm_sv=abc; JSESSIONID=def"
    assert auth_service.logout() is True
    assert auth_service.get_session() is None
