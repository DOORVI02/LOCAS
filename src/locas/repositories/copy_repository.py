"""Book copy repository for database operations."""

from typing import Any

from locas.core.constants import BookCopyStatus
from locas.core.exceptions import DuplicateError
from locas.models.book_copy import BookCopy, BookCopyCreate, BookCopyUpdate
from locas.repositories.base_repository import BaseRepository


class CopyRepository(BaseRepository[BookCopy]):
    """Repository for BookCopy entity operations."""

    @property
    def table_name(self) -> str:
        return "book_copies"

    @property
    def primary_key(self) -> str:
        return "copy_id"

    def _from_row(self, row: dict[str, Any]) -> BookCopy:
        return BookCopy.from_dict(row)

    def find_by_barcode(self, barcode: str) -> BookCopy | None:
        """Find a copy by barcode.

        Args:
            barcode: Barcode to search for.

        Returns:
            BookCopy instance or None.
        """
        query = """
            SELECT bc.*, b.title, b.author, b.isbn
            FROM book_copies bc
            JOIN books b ON bc.book_id = b.book_id
            WHERE bc.barcode = %s
        """
        row = self.db.execute_one(query, (barcode,))
        return self._from_row(row) if row else None

    def find_by_book(self, book_id: int, status: BookCopyStatus | None = None) -> list[BookCopy]:
        """Find all copies of a book.

        Args:
            book_id: Book ID.
            status: Optional status filter.

        Returns:
            List of BookCopy instances.
        """
        if status:
            query = """
                SELECT bc.*, b.title, b.author, b.isbn
                FROM book_copies bc
                JOIN books b ON bc.book_id = b.book_id
                WHERE bc.book_id = %s AND bc.status = %s
                ORDER BY bc.barcode
            """
            rows = self.db.execute(query, (book_id, str(status)))
        else:
            query = """
                SELECT bc.*, b.title, b.author, b.isbn
                FROM book_copies bc
                JOIN books b ON bc.book_id = b.book_id
                WHERE bc.book_id = %s
                ORDER BY bc.barcode
            """
            rows = self.db.execute(query, (book_id,))

        return [self._from_row(row) for row in rows]

    def find_available_copy(self, book_id: int) -> BookCopy | None:
        """Find an available copy of a book.

        Args:
            book_id: Book ID.

        Returns:
            First available BookCopy or None.
        """
        query = """
            SELECT bc.*, b.title, b.author, b.isbn
            FROM book_copies bc
            JOIN books b ON bc.book_id = b.book_id
            WHERE bc.book_id = %s AND bc.status = 'available'
            LIMIT 1
        """
        row = self.db.execute_one(query, (book_id,))
        return self._from_row(row) if row else None

    def find_all_with_books(
        self,
        limit: int = 100,
        offset: int = 0,
        status: BookCopyStatus | None = None,
        book_id: int | None = None,
    ) -> list[BookCopy]:
        """Find copies with book details.

        Args:
            limit: Maximum records.
            offset: Records to skip.
            status: Optional status filter.
            book_id: Optional book filter.

        Returns:
            List of BookCopy instances with book details.
        """
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("bc.status = %s")
            params.append(str(status))

        if book_id:
            conditions.append("bc.book_id = %s")
            params.append(book_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT bc.*, b.title, b.author, b.isbn
            FROM book_copies bc
            JOIN books b ON bc.book_id = b.book_id
            WHERE {where_clause}
            ORDER BY b.title, bc.barcode
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def create(self, copy_data: BookCopyCreate) -> int:
        """Create a new book copy.

        Args:
            copy_data: BookCopy creation DTO.

        Returns:
            New copy's ID.

        Raises:
            DuplicateError: If barcode already exists.
        """
        if self.find_by_barcode(copy_data.barcode):
            raise DuplicateError(f"Barcode '{copy_data.barcode}' already exists")

        data = {
            "book_id": copy_data.book_id,
            "barcode": copy_data.barcode,
            "status": "available",
        }

        if copy_data.location:
            data["location"] = copy_data.location

        query, params = self._build_insert_query(data)
        return self.db.execute_insert(query, params)

    def update(self, copy_id: int, update_data: BookCopyUpdate) -> bool:
        """Update a book copy.

        Args:
            copy_id: Copy ID to update.
            update_data: Update DTO.

        Returns:
            True if updated.
        """
        data = update_data.to_update_dict()
        if not data:
            return False

        query, params = self._build_update_query(copy_id, data)
        affected = self.db.execute_update(query, params)
        return affected > 0

    def update_status(self, copy_id: int, status: BookCopyStatus) -> bool:
        """Update the status of a copy.

        Args:
            copy_id: Copy ID.
            status: New status.

        Returns:
            True if updated.
        """
        query = "UPDATE book_copies SET status = %s WHERE copy_id = %s"
        affected = self.db.execute_update(query, (str(status), copy_id))
        return affected > 0

    def count_by_status(self, status: BookCopyStatus) -> int:
        """Count copies with a specific status.

        Args:
            status: Status to count.

        Returns:
            Count of copies.
        """
        return self.count("status = %s", (str(status),))

    def count_by_book(self, book_id: int) -> dict[str, int]:
        """Count copies of a book by status.

        Args:
            book_id: Book ID.

        Returns:
            Dictionary of status -> count.
        """
        query = """
            SELECT status, COUNT(*) as cnt
            FROM book_copies
            WHERE book_id = %s
            GROUP BY status
        """
        rows = self.db.execute(query, (book_id,))
        return {row["status"]: row["cnt"] for row in rows}
