from __future__ import annotations

from fusionctl.exceptions import AuthenticationError
from fusionctl.models.session import Session
from fusionctl.storage.secrets import SecretStore


class AuthService:
    def __init__(self, secret_store: SecretStore) -> None:
        self.secret_store = secret_store

    def login_with_cookie(self, cookie_header: str) -> Session:
        token = cookie_header.strip()
        self._validate_cookie_header(token)
        session = Session(token=token)
        self.secret_store.save_session(session)
        return session

    def logout(self) -> bool:
        return self.secret_store.clear_session()

    def get_session(self) -> Session | None:
        return self.secret_store.get_session()

    def require_session(self) -> Session:
        session = self.get_session()
        if session is None or not session.is_valid:
            raise AuthenticationError("Not authenticated. Use 'fusionctl auth login' to begin.")
        return session

    def status(self) -> tuple[bool, Session | None]:
        session = self.get_session()
        if session is None:
            return False, None
        return session.is_valid, session

    def _validate_cookie_header(self, token: str) -> None:
        if "=" not in token or ";" in token and not any(part.strip().count("=") >= 1 for part in token.split(";")):
            raise AuthenticationError("Token must look like an HTTP Cookie header")
        if len(token) < 8:
            raise AuthenticationError("Token is too short to be a valid Oracle session cookie")
