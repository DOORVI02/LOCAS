from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from locas.core.exceptions import BusinessRuleError
from locas.repositories.book_repository import BookRepository
from locas.repositories.copy_repository import CopyRepository
from locas.repositories.fine_repository import FineRepository
from locas.repositories.transaction_repository import TransactionRepository
from locas.repositories.user_repository import UserRepository
from locas.services.transaction_service import TransactionService


@pytest.fixture
def mock_txn_repo():
    return MagicMock(spec=TransactionRepository)

@pytest.fixture
def mock_copy_repo():
    return MagicMock(spec=CopyRepository)

@pytest.fixture
def mock_user_repo():
    return MagicMock(spec=UserRepository)

@pytest.fixture
def mock_fine_repo():
    return MagicMock(spec=FineRepository)

@pytest.fixture
def mock_book_repo():
    return MagicMock(spec=BookRepository)

@pytest.fixture
def txn_service(mock_txn_repo, mock_copy_repo, mock_user_repo, mock_fine_repo, mock_book_repo):
    config = MagicMock()
    config.max_borrow_limit = 3
    config.max_fine_threshold = 100.0
    config.max_borrow_days = 14
    config.fine_rate_per_day = 5.0

    db_manager = MagicMock()
    session_manager = MagicMock()

    # Mock session for require_librarian check if needed
    session_manager.current_session = MagicMock()
    session_manager.current_session.has_role.return_value = True
    session_manager.current_session.user_id = 1

    service = TransactionService(config, db_manager, session_manager)
    service.trans_repo = mock_txn_repo
    service.copy_repo = mock_copy_repo
    service.user_repo = mock_user_repo
    service.fine_repo = mock_fine_repo
    service.book_repo = mock_book_repo
    service.audit_repo = MagicMock()
    return service

def test_issue_book_success(txn_service, mock_copy_repo, mock_user_repo, mock_txn_repo, mock_fine_repo, mock_book_repo):
    # Setup - use find_by_id instead of get_by_id
    # Mock Copy object needs to be an object, not dict, if service expects object attributes,
    # but based on my quick look, repo usually returns objects.
    # Let's return MagicMocks that behave like objects.

    # Note: TransactionService likely expects objects because it accesses attributes.
    copy_mock = MagicMock()
    copy_mock.copy_id = 1
    copy_mock.status = "available"
    copy_mock.book_id = 100
    mock_copy_repo.find_by_id.return_value = copy_mock

    user_mock = MagicMock()
    user_mock.user_id = 2
    user_mock.role_id = 3
    user_mock.role_name = "student"
    user_mock.is_active = True
    mock_user_repo.find_by_id.return_value = user_mock

    mock_txn_repo.count_active_by_user.return_value = 0
    mock_txn_repo.create.return_value = 500
    mock_fine_repo.get_total_pending_by_user.return_value = Decimal("0.0")

    # Mock the transaction object returned by find_by_id (called by get_transaction)
    returned_txn = MagicMock()
    returned_txn.transaction_id = 500
    mock_txn_repo.find_by_id.return_value = returned_txn

    # Action
    txn = txn_service.issue_book(copy_id=1, student_id=2)

    # Assert - issue_book returns Transaction object, not ID
    assert txn.transaction_id == 500
    mock_copy_repo.update_status.assert_called_once()
    mock_txn_repo.create.assert_called_once()
    mock_book_repo.update_copy_counts.assert_called_with(100)

def test_issue_limit_exceeded(txn_service, mock_copy_repo, mock_user_repo, mock_txn_repo, mock_fine_repo):
    copy_mock = MagicMock()
    copy_mock.copy_id = 1
    copy_mock.status = "available"
    mock_copy_repo.find_by_id.return_value = copy_mock

    user_mock = MagicMock()
    user_mock.user_id = 2
    user_mock.role_id = 3
    user_mock.role_name = "student"
    user_mock.is_active = True
    mock_user_repo.find_by_id.return_value = user_mock

    # Limit is 3
    mock_txn_repo.count_active_by_user.return_value = 3
    mock_fine_repo.get_total_pending_by_user.return_value = Decimal("0.0")

    with pytest.raises(BusinessRuleError, match="borrowing limit"):
        txn_service.issue_book(copy_id=1, student_id=2)
