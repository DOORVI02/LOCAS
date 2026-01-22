from unittest.mock import MagicMock

import pytest

from locas.core.exceptions import AuthenticationError
from locas.core.security import SecurityManager, SessionManager
from locas.repositories.audit_repository import AuditRepository
from locas.repositories.user_repository import UserRepository
from locas.services.auth_service import AuthService


@pytest.fixture
def mock_user_repo():
    return MagicMock(spec=UserRepository)

@pytest.fixture
def mock_audit_repo():
    return MagicMock(spec=AuditRepository)

@pytest.fixture
def auth_service(mock_user_repo, mock_audit_repo):
    config = MagicMock()
    db_manager = MagicMock()
    session_manager = MagicMock(spec=SessionManager)

    # We need to patch SecurityManager execution inside __init__ or just let it happen and mock the attribute later
    # Since SecurityManager requires config, and we pass a mock config, it should be fine if SecurityManager doesn't do heavy lifting in init.
    # SecurityManager(config) only sets self.config.

    service = AuthService(config, db_manager, session_manager)
    service.user_repo = mock_user_repo
    service.audit_repo = mock_audit_repo

    # Mock specific security methods we rely on
    service.security = MagicMock(spec=SecurityManager)
    service.security.hash_password.side_effect = lambda p: f"hashed_{p}"
    service.security.verify_password.side_effect = lambda p, h: h == f"hashed_{p}"

    return service

def test_login_success(auth_service, mock_user_repo):
    # Mock user data
    start_user = {
        "user_id": 1,
        "username": "admin",
        "password_hash": "hashed_admin123",
        "role_id": 1,
        "role_name": "admin",
        "full_name": "Administrator",
        "is_active": 1
    }
    mock_user_repo.find_with_password.return_value = start_user

    session = auth_service.authenticate("admin", "admin123")

    assert session is not None
    mock_user_repo.update_last_login.assert_called_once()
    auth_service.session_manager.create_session.assert_called_once()

def test_login_invalid_password(auth_service, mock_user_repo):
    start_user = {
        "user_id": 1,
        "username": "admin",
        "password_hash": "hashed_admin123",
        "role_id": 1,
        "is_active": 1
    }
    mock_user_repo.find_with_password.return_value = start_user

    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        auth_service.authenticate("admin", "wrongpass")

def test_login_user_not_found(auth_service, mock_user_repo):
    mock_user_repo.find_with_password.return_value = None

    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        auth_service.authenticate("unknown", "pass")
