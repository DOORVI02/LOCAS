"""Book management service for LOCAS."""

from locas.config import Config
from locas.core.constants import AuditAction, BookCopyStatus
from locas.core.database import DatabaseManager
from locas.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from locas.core.security import SessionManager
from locas.models.book import Book, BookCreate, BookUpdate
from locas.models.book_copy import BookCopy, BookCopyCreate, BookCopyUpdate
from locas.repositories.audit_repository import AuditRepository
from locas.repositories.book_repository import BookRepository
from locas.repositories.copy_repository import CopyRepository
from locas.utils.validators import validate_barcode, validate_isbn


class BookService:
    """Handles book catalog and copy management.

    Responsibilities:
    - Book CRUD operations
    - Book copy management
    - Book search
    - Availability tracking

    Attributes:
        config: Application configuration.
        session_manager: Session manager.
        book_repo: Book repository.
        copy_repo: Copy repository.
        audit_repo: Audit repository.
    """

    def __init__(
        self, config: Config, db_manager: DatabaseManager, session_manager: SessionManager
    ) -> None:
        """Initialize BookService.

        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
        """
        self.config = config
        self.session_manager = session_manager
        self.book_repo = BookRepository(db_manager)
        self.copy_repo = CopyRepository(db_manager)
        self.audit_repo = AuditRepository(db_manager)

    def _require_librarian(self) -> int:
        """Require librarian role and return current user ID.

        Returns:
            Current user's ID.

        Raises:
            AuthorizationError: If not librarian or admin.
        """
        session = self.session_manager.current_session
        if session is None or not session.has_role("librarian", "admin"):
            raise AuthorizationError("Librarian privileges required")
        return session.user_id

    # -------------------------------------------------------------------------
    # Book Operations
    # -------------------------------------------------------------------------

    def get_book(self, book_id: int) -> Book:
        """Get a book by ID.

        Args:
            book_id: Book ID.

        Returns:
            Book instance.

        Raises:
            NotFoundError: If book not found.
        """
        book = self.book_repo.find_by_id(book_id)
        if book is None:
            raise NotFoundError(f"Book with ID {book_id} not found")
        return book

    def get_book_by_isbn(self, isbn: str) -> Book:
        """Get a book by ISBN.

        Args:
            isbn: Book ISBN.

        Returns:
            Book instance.

        Raises:
            NotFoundError: If book not found.
        """
        book = self.book_repo.find_by_isbn(isbn)
        if book is None:
            raise NotFoundError(f"Book with ISBN '{isbn}' not found")
        return book

    def list_books(self, limit: int = 100, offset: int = 0, order_by: str = "title") -> list[Book]:
        """List all books.

        Args:
            limit: Maximum records.
            offset: Records to skip.
            order_by: Column to order by.

        Returns:
            List of Book instances.
        """
        return self.book_repo.find_all(limit=limit, offset=offset, order_by=order_by)

    def search_books(
        self,
        query: str | None = None,
        category: str | None = None,
        available_only: bool = False,
        limit: int = 100,
    ) -> list[Book]:
        """Search books with filters.

        Args:
            query: Search text.
            category: Category filter.
            available_only: Only show available books.
            limit: Maximum records.

        Returns:
            List of matching Book instances.
        """
        if query:
            # Try simple search (more reliable than fulltext for short queries)
            return self.book_repo.search_simple(query, limit=limit)
        else:
            return self.book_repo.search(
                query_text=query, category=category, available_only=available_only, limit=limit
            )

    def get_categories(self) -> list[str]:
        """Get all book categories.

        Returns:
            List of category names.
        """
        return self.book_repo.get_categories()

    def create_book(self, book_data: BookCreate) -> Book:
        """Create a new book.

        Args:
            book_data: Book creation data.

        Returns:
            Created Book instance.

        Raises:
            AuthorizationError: If not librarian.
            ValidationError: If validation fails.
            DuplicateError: If ISBN exists.
        """
        user_id = self._require_librarian()

        # Validate ISBN
        validate_isbn(book_data.isbn)

        # Validate required fields
        if not book_data.title or not book_data.title.strip():
            raise ValidationError("Book title is required")

        if not book_data.author or not book_data.author.strip():
            raise ValidationError("Book author is required")

        # Create book
        book_id = self.book_repo.create(book_data)

        # Log action
        self.audit_repo.log_action(
            user_id=user_id,
            action=AuditAction.BOOK_CREATED,
            entity_type="book",
            entity_id=book_id,
            new_value={
                "isbn": book_data.isbn,
                "title": book_data.title,
                "author": book_data.author,
            },
        )

        return self.get_book(book_id)

    def update_book(self, book_id: int, update_data: BookUpdate) -> Book:
        """Update a book.

        Args:
            book_id: Book ID.
            update_data: Fields to update.

        Returns:
            Updated Book instance.

        Raises:
            AuthorizationError: If not librarian.
            NotFoundError: If book not found.
        """
        user_id = self._require_librarian()

        # Get existing book
        existing = self.get_book(book_id)
        old_value = existing.to_dict()

        # Validate ISBN if changing
        if update_data.isbn is not None:
            validate_isbn(update_data.isbn)

        # Update book
        self.book_repo.update(book_id, update_data)

        # Get updated book
        updated = self.get_book(book_id)

        # Log action
        self.audit_repo.log_action(
            user_id=user_id,
            action=AuditAction.BOOK_UPDATED,
            entity_type="book",
            entity_id=book_id,
            old_value=old_value,
            new_value=updated.to_dict(),
        )

        return updated

    def delete_book(self, book_id: int) -> bool:
        """Delete a book.

        Args:
            book_id: Book ID.

        Returns:
            True if deleted.

        Raises:
            AuthorizationError: If not librarian.
            NotFoundError: If book not found.
            ValidationError: If book has issued copies.
        """
        user_id = self._require_librarian()

        # Verify book exists
        book = self.get_book(book_id)

        # Check for issued copies
        issued_count = self.copy_repo.count_by_book(book_id).get("issued", 0)
        if issued_count > 0:
            raise ValidationError(
                f"Cannot delete book with {issued_count} issued copies. Return all copies first."
            )

        # Delete (will cascade to copies)
        success = self.book_repo.delete(book_id)

        if success:
            self.audit_repo.log_action(
                user_id=user_id,
                action=AuditAction.BOOK_DELETED,
                entity_type="book",
                entity_id=book_id,
                old_value=book.to_dict(),
            )

        return success

    # -------------------------------------------------------------------------
    # Copy Operations
    # -------------------------------------------------------------------------

    def get_copy(self, copy_id: int) -> BookCopy:
        """Get a book copy by ID.

        Args:
            copy_id: Copy ID.

        Returns:
            BookCopy instance.

        Raises:
            NotFoundError: If copy not found.
        """
        copy = self.copy_repo.find_by_id(copy_id)
        if copy is None:
            raise NotFoundError(f"Copy with ID {copy_id} not found")
        return copy

    def get_copy_by_barcode(self, barcode: str) -> BookCopy:
        """Get a copy by barcode.

        Args:
            barcode: Copy barcode.

        Returns:
            BookCopy instance.

        Raises:
            NotFoundError: If copy not found.
        """
        copy = self.copy_repo.find_by_barcode(barcode)
        if copy is None:
            raise NotFoundError(f"Copy with barcode '{barcode}' not found")
        return copy

    def list_copies(
        self,
        book_id: int | None = None,
        status: BookCopyStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BookCopy]:
        """List book copies with filters.

        Args:
            book_id: Filter by book.
            status: Filter by status.
            limit: Maximum records.
            offset: Records to skip.

        Returns:
            List of BookCopy instances.
        """
        return self.copy_repo.find_all_with_books(
            limit=limit, offset=offset, status=status, book_id=book_id
        )

    def get_copies_by_book(self, book_id: int) -> list[BookCopy]:
        """Get all copies of a book.

        Args:
            book_id: Book ID.

        Returns:
            List of BookCopy instances.
        """
        return self.copy_repo.find_by_book(book_id)

    def add_copy(self, copy_data: BookCopyCreate) -> BookCopy:
        """Add a new copy of a book.

        Args:
            copy_data: Copy creation data.

        Returns:
            Created BookCopy instance.

        Raises:
            AuthorizationError: If not librarian.
            NotFoundError: If book not found.
            DuplicateError: If barcode exists.
        """
        user_id = self._require_librarian()

        # Verify book exists
        book = self.get_book(copy_data.book_id)

        # Validate barcode
        validate_barcode(copy_data.barcode)

        # Create copy
        copy_id = self.copy_repo.create(copy_data)

        # Refresh book copy counts
        self.book_repo.update_copy_counts(copy_data.book_id)

        # Log action
        self.audit_repo.log_action(
            user_id=user_id,
            action=AuditAction.COPY_ADDED,
            entity_type="book_copy",
            entity_id=copy_id,
            new_value={
                "book_id": copy_data.book_id,
                "barcode": copy_data.barcode,
                "book_title": book.title,
            },
        )

        return self.get_copy(copy_id)

    def update_copy(self, copy_id: int, update_data: BookCopyUpdate) -> BookCopy:
        """Update a book copy.

        Args:
            copy_id: Copy ID.
            update_data: Fields to update.

        Returns:
            Updated BookCopy instance.
        """
        user_id = self._require_librarian()

        # Verify copy exists
        existing = self.get_copy(copy_id)

        # Update
        self.copy_repo.update(copy_id, update_data)

        # Refresh counts if status changed
        if update_data.status is not None:
            self.book_repo.update_copy_counts(existing.book_id)

        # Log action
        self.audit_repo.log_action(
            user_id=user_id,
            action=AuditAction.COPY_UPDATED,
            entity_type="book_copy",
            entity_id=copy_id,
            new_value=update_data.to_update_dict(),
        )

        return self.get_copy(copy_id)

    def mark_copy_lost(self, copy_id: int) -> BookCopy:
        """Mark a copy as lost.

        Args:
            copy_id: Copy ID.

        Returns:
            Updated BookCopy instance.
        """
        user_id = self._require_librarian()

        copy = self.get_copy(copy_id)

        self.copy_repo.update_status(copy_id, BookCopyStatus.LOST)
        self.book_repo.update_copy_counts(copy.book_id)

        self.audit_repo.log_action(
            user_id=user_id,
            action=AuditAction.COPY_MARKED_LOST,
            entity_type="book_copy",
            entity_id=copy_id,
        )

        return self.get_copy(copy_id)

    def mark_copy_damaged(self, copy_id: int) -> BookCopy:
        """Mark a copy as damaged.

        Args:
            copy_id: Copy ID.

        Returns:
            Updated BookCopy instance.
        """
        user_id = self._require_librarian()

        copy = self.get_copy(copy_id)

        self.copy_repo.update_status(copy_id, BookCopyStatus.DAMAGED)
        self.book_repo.update_copy_counts(copy.book_id)

        self.audit_repo.log_action(
            user_id=user_id,
            action=AuditAction.COPY_MARKED_DAMAGED,
            entity_type="book_copy",
            entity_id=copy_id,
        )

        return self.get_copy(copy_id)

    def delete_copy(self, copy_id: int) -> bool:
        """Delete a book copy.

        Args:
            copy_id: Copy ID.

        Returns:
            True if deleted.

        Raises:
            ValidationError: If copy is currently issued.
        """
        user_id = self._require_librarian()

        copy = self.get_copy(copy_id)

        if copy.status == BookCopyStatus.ISSUED:
            raise ValidationError("Cannot delete an issued copy. Return it first.")

        book_id = copy.book_id
        success = self.copy_repo.delete(copy_id)

        if success:
            self.book_repo.update_copy_counts(book_id)
            self.audit_repo.log_action(
                user_id=user_id,
                action=AuditAction.COPY_REMOVED,
                entity_type="book_copy",
                entity_id=copy_id,
                old_value={"barcode": copy.barcode, "book_id": book_id},
            )

        return success

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_book_stats(self) -> dict:
        """Get book statistics.

        Returns:
            Dictionary with statistics.
        """
        return {
            "total_books": self.book_repo.count_total(),
            "available_books": self.book_repo.count_available(),
            "total_copies": self.copy_repo.count(),
            "available_copies": self.copy_repo.count_by_status(BookCopyStatus.AVAILABLE),
            "issued_copies": self.copy_repo.count_by_status(BookCopyStatus.ISSUED),
            "lost_copies": self.copy_repo.count_by_status(BookCopyStatus.LOST),
            "damaged_copies": self.copy_repo.count_by_status(BookCopyStatus.DAMAGED),
        }

    def get_popular_books(self, limit: int = 10) -> list[dict]:
        """Get most popular books.

        Args:
            limit: Number of books.

        Returns:
            List of books with issue counts.
        """
        return self.book_repo.get_popular_books(limit)
