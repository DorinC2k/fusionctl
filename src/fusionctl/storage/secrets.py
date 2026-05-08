from __future__ import annotations

from pathlib import Path

import keyring
import orjson
from keyring.errors import KeyringError

from fusionctl.exceptions import StorageError
from fusionctl.models.session import Session

SERVICE_NAME = "fusionctl"
SESSION_KEY = "oracle_session"


class SecretStore:
    """Session storage that prefers OS keychain and falls back to a local file."""

    def __init__(self, fallback_path: Path) -> None:
        self.fallback_path = fallback_path

    def get_session(self) -> Session | None:
        payload = self._get_keyring_payload()
        if payload is None:
            payload = self._get_file_payload()
        if payload is None:
            return None
        return Session.model_validate_json(payload)

    def save_session(self, session: Session) -> None:
        payload = session.model_dump_json()
        if self._set_keyring_payload(payload):
            self._delete_file()
            return
        self._set_file_payload(payload)

    def clear_session(self) -> bool:
        removed = False
        try:
            keyring.delete_password(SERVICE_NAME, SESSION_KEY)
            removed = True
        except KeyringError:
            pass
        except keyring.errors.PasswordDeleteError:
            pass

        if self.fallback_path.exists():
            self.fallback_path.unlink()
            removed = True
        return removed

    def _get_keyring_payload(self) -> str | None:
        try:
            return keyring.get_password(SERVICE_NAME, SESSION_KEY)
        except KeyringError:
            return None

    def _set_keyring_payload(self, payload: str) -> bool:
        try:
            keyring.set_password(SERVICE_NAME, SESSION_KEY, payload)
        except KeyringError:
            return False
        return True

    def _get_file_payload(self) -> str | None:
        if not self.fallback_path.exists():
            return None
        try:
            return self.fallback_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Could not read session file: {exc}") from exc

    def _set_file_payload(self, payload: str) -> None:
        try:
            self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
            self.fallback_path.write_bytes(orjson.dumps(orjson.loads(payload)))
            self.fallback_path.chmod(0o600)
        except OSError as exc:
            raise StorageError(f"Could not write session file: {exc}") from exc

    def _delete_file(self) -> None:
        try:
            if self.fallback_path.exists():
                self.fallback_path.unlink()
        except OSError as exc:
            raise StorageError(f"Could not delete session file: {exc}") from exc
