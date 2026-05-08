from pathlib import Path

import pytest

from fusionctl.services.auth_service import AuthService
from fusionctl.storage.secrets import SecretStore


@pytest.fixture
def auth_service(tmp_path: Path) -> AuthService:
    return AuthService(SecretStore(tmp_path / "session.json"))
