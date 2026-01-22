from unittest.mock import MagicMock

import pytest

from locas.models.book import BookCreate
from locas.repositories.book_repository import BookRepository
from locas.repositories.copy_repository import CopyRepository
from locas.services.book_service import BookService


@pytest.fixture
def mock_book_repo():
    return MagicMock(spec=BookRepository)

@pytest.fixture
def mock_copy_repo():
    return MagicMock(spec=CopyRepository)

@pytest.fixture
def book_service(mock_book_repo, mock_copy_repo):
    config = MagicMock()
    db_manager = MagicMock()
    session_manager = MagicMock()

    # Mock active session with librarian role
    session_manager.current_session = MagicMock()
    session_manager.current_session.has_role.return_value = True
    session_manager.current_session.user_id = 1

    service = BookService(config, db_manager, session_manager)
    service.book_repo = mock_book_repo
    service.copy_repo = mock_copy_repo
    # Mock audit repo since create_book logs actions
    service.audit_repo = MagicMock()

    return service

def test_add_book_success(book_service, mock_book_repo):
    book_data = BookCreate(
        title="Python Programming",
        author="John Doe",
        isbn="9780134444321",
        category="Education"
    )
    mock_book_repo.create.return_value = 1

    # Mock get_book because create_book calls it to return the new book
    mock_book_repo.find_by_id.return_value = MagicMock()

    book = book_service.create_book(book_data)

    assert book is not None
    mock_book_repo.create.assert_called_once()

def test_search_books(book_service, mock_book_repo):
    # search_books with query calls search_simple
    mock_book_repo.search_simple.return_value = [
        MagicMock(title="Python 101", author="Jane Doe")
    ]

    results = book_service.search_books("Python")

    assert len(results) == 1
    assert results[0].title == "Python 101"
