from fusionctl.services.browser_auth_service import cookie_header_from_playwright


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
