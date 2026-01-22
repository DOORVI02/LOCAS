"""Book repository for database operations."""

from typing import Any

from locas.core.exceptions import DuplicateError
from locas.models.book import Book, BookCreate, BookUpdate
from locas.repositories.base_repository import BaseRepository


class BookRepository(BaseRepository[Book]):
    """Repository for Book entity operations."""

    @property
    def table_name(self) -> str:
        return "books"

    @property
    def primary_key(self) -> str:
        return "book_id"

    def _from_row(self, row: dict[str, Any]) -> Book:
        return Book.from_dict(row)

    def find_by_isbn(self, isbn: str) -> Book | None:
        """Find a book by ISBN.

        Args:
            isbn: ISBN to search for.

        Returns:
            Book instance or None.
        """
        query = "SELECT * FROM books WHERE isbn = %s"
        row = self.db.execute_one(query, (isbn,))
        return self._from_row(row) if row else None

    def search(
        self,
        query_text: str | None = None,
        category: str | None = None,
        available_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Book]:
        """Search books with filters.

        Args:
            query_text: Search in title, author, description.
            category: Filter by category.
            available_only: Only show books with available copies.
            limit: Maximum records.
            offset: Records to skip.

        Returns:
            List of matching Book instances.
        """
        conditions = []
        params: list[Any] = []

        if query_text:
            conditions.append(
                "MATCH(title, author, description) AGAINST (%s IN NATURAL LANGUAGE MODE)"
            )
            params.append(query_text)

        if category:
            conditions.append("category = %s")
            params.append(category)

        if available_only:
            conditions.append("available_copies > 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM books
            WHERE {where_clause}
            ORDER BY title ASC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def search_simple(self, query_text: str, limit: int = 100, offset: int = 0) -> list[Book]:
        """Simple LIKE-based search for books.

        Fallback when fulltext search is not available.

        Args:
            query_text: Search text.
            limit: Maximum records.
            offset: Records to skip.

        Returns:
            List of matching Book instances.
        """
        pattern = f"%{query_text}%"
        query = """
            SELECT * FROM books
            WHERE title LIKE %s
               OR author LIKE %s
               OR isbn LIKE %s
               OR description LIKE %s
            ORDER BY title ASC
            LIMIT %s OFFSET %s
        """
        params = (pattern, pattern, pattern, pattern, limit, offset)

        rows = self.db.execute(query, params)
        return [self._from_row(row) for row in rows]

    def get_categories(self) -> list[str]:
        """Get list of all unique categories.

        Returns:
            List of category names.
        """
        query = """
            SELECT DISTINCT category
            FROM books
            WHERE category IS NOT NULL
            ORDER BY category
        """
        rows = self.db.execute(query)
        return [row["category"] for row in rows]

    def create(self, book_data: BookCreate) -> int:
        """Create a new book.

        Args:
            book_data: Book creation DTO.

        Returns:
            New book's ID.

        Raises:
            DuplicateError: If ISBN already exists.
        """
        if self.find_by_isbn(book_data.isbn):
            raise DuplicateError(f"ISBN '{book_data.isbn}' already exists")

        data = {
            "isbn": book_data.isbn,
            "title": book_data.title,
            "author": book_data.author,
            "publisher": book_data.publisher,
            "publication_year": book_data.publication_year,
            "category": book_data.category,
            "description": book_data.description,
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        query, params = self._build_insert_query(data)
        return self.db.execute_insert(query, params)

    def update(self, book_id: int, update_data: BookUpdate) -> bool:
        """Update a book.

        Args:
            book_id: Book ID to update.
            update_data: Update DTO.

        Returns:
            True if updated.
        """
        data = update_data.to_update_dict()
        if not data:
            return False

        # Check ISBN duplicate if changing
        if "isbn" in data:
            existing = self.find_by_isbn(data["isbn"])
            if existing and existing.book_id != book_id:
                raise DuplicateError(f"ISBN '{data['isbn']}' already exists")

        query, params = self._build_update_query(book_id, data)
        affected = self.db.execute_update(query, params)
        return affected > 0

    def update_copy_counts(self, book_id: int) -> bool:
        """Recalculate copy counts for a book.

        Args:
            book_id: Book ID.

        Returns:
            True if updated.
        """
        query = """
            UPDATE books b
            SET
                total_copies = (
                    SELECT COUNT(*) FROM book_copies
                    WHERE book_id = b.book_id
                ),
                available_copies = (
                    SELECT COUNT(*) FROM book_copies
                    WHERE book_id = b.book_id AND status = 'available'
                )
            WHERE book_id = %s
        """
        affected = self.db.execute_update(query, (book_id,))
        return affected > 0

    def get_popular_books(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most popular books by issue count.

        Args:
            limit: Number of books to return.

        Returns:
            List of books with issue counts.
        """
        query = """
            SELECT b.*, COUNT(t.transaction_id) as issue_count
            FROM books b
            JOIN book_copies bc ON b.book_id = bc.book_id
            JOIN transactions t ON bc.copy_id = t.copy_id
            GROUP BY b.book_id
            ORDER BY issue_count DESC
            LIMIT %s
        """
        return self.db.execute(query, (limit,))

    def count_total(self) -> int:
        """Get total number of books."""
        return self.count()

    def count_available(self) -> int:
        """Get count of books with available copies."""
        return self.count("available_copies > 0")
