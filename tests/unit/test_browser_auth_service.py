from fusionctl.services.browser_auth_service import _is_target_closed_error
from fusionctl.services.browser_auth_service import cookie_header_from_playwright
from fusionctl.services.browser_auth_service import has_oracle_session_cookie


def test_cookie_header_from_playwright_keeps_oracle_cookies_only() -> None:
    header = cookie_header_from_playwright(
        [
            {"domain": ".example.com", "name": "ignored", "value": "nope"},
            {"domain": ".eclf.fa.em2.oraclecloud.com", "name": "JSESSIONID", "value": "abc"},
            {"domain": ".oracle.endava.com", "name": "OAMAuthnCookie", "value": "def"},
            {"domain": ".eclf.fa.em2.oraclecloud.com", "name": "", "value": "missing-name"},
        ]
    )

    assert "JSESSIONID=abc" in header
    assert "OAMAuthnCookie=def" in header
    assert "ignored=nope" not in header


def test_target_closed_error_is_detected_by_message() -> None:
    assert _is_target_closed_error(
        RuntimeError("Page.wait_for_timeout: Target page, context or browser has been closed")
    )


def test_has_oracle_session_cookie_detects_existing_browser_login() -> None:
    assert has_oracle_session_cookie(
        [
            {"domain": ".example.com", "name": "JSESSIONID", "value": "wrong-domain"},
            {"domain": ".eclf.fa.em2.oraclecloud.com", "name": "JSESSIONID", "value": "abc"},
        ]
    )


def test_has_oracle_session_cookie_rejects_missing_session_cookie() -> None:
    assert not has_oracle_session_cookie(
        [{"domain": ".eclf.fa.em2.oraclecloud.com", "name": "ignored", "value": "abc"}]
    )
