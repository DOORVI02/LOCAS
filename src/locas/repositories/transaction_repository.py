"""Transaction repository for database operations."""

from typing import Any

from locas.core.constants import TransactionStatus
from locas.models.transaction import Transaction, TransactionCreate
from locas.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction entity operations."""

    @property
    def table_name(self) -> str:
        return "transactions"

    @property
    def primary_key(self) -> str:
        return "transaction_id"

    def _from_row(self, row: dict[str, Any]) -> Transaction:
        return Transaction.from_dict(row)

    def find_by_id(self, transaction_id: int) -> Transaction | None:
        """Find transaction by ID with related data."""
        query = """

            SELECT t.*,
                   bc.barcode,
                   b.book_id, b.isbn, b.title, b.author,
                   u.full_name as borrower_name, u.username as borrower_username,
                   lib.full_name as issued_by_name,
                   ret.full_name as returned_by_name,
                   DATEDIFF(CURDATE(), t.due_date) as days_overdue
            FROM transactions t
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            JOIN users lib ON t.issued_by = lib.user_id
            LEFT JOIN users ret ON t.returned_by = ret.user_id
            WHERE t.transaction_id = %s
        """
        row = self.db.execute_one(query, (transaction_id,))
        return self._from_row(row) if row else None

    def find_active_by_copy(self, copy_id: int) -> Transaction | None:
        """Find active transaction for a copy.

        Args:
            copy_id: Book copy ID.

        Returns:
            Active Transaction or None.
        """
        query = """

            SELECT t.*,
                   bc.barcode,
                   b.book_id, b.isbn, b.title, b.author,
                   u.full_name as borrower_name, u.username as borrower_username,
                   lib.full_name as issued_by_name
            FROM transactions t
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            JOIN users lib ON t.issued_by = lib.user_id
            WHERE t.copy_id = %s AND t.status IN ('active', 'overdue')
        """
        row = self.db.execute_one(query, (copy_id,))
        return self._from_row(row) if row else None

    def find_by_user(
        self,
        user_id: int,
        status: TransactionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """Find transactions for a user.

        Args:
            user_id: User ID.
            status: Optional status filter.
            limit: Maximum records.
            offset: Records to skip.

        Returns:
            List of Transaction instances.
        """
        conditions = ["t.user_id = %s"]
        params: list[Any] = [user_id]

        if status:
            conditions.append("t.status = %s")
            params.append(str(status))

        where_clause = " AND ".join(conditions)

        query = f"""

            SELECT t.*,
                   bc.barcode,
                   b.book_id, b.isbn, b.title, b.author,
                   u.full_name as borrower_name, u.username as borrower_username,
                   lib.full_name as issued_by_name,
                   DATEDIFF(CURDATE(), t.due_date) as days_overdue
            FROM transactions t
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            JOIN users lib ON t.issued_by = lib.user_id
            WHERE {where_clause}
            ORDER BY t.issue_date DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def find_active_by_user(self, user_id: int) -> list[Transaction]:
        """Find active transactions for a user.

        Args:
            user_id: User ID.

        Returns:
            List of active Transaction instances.
        """
        query = """

            SELECT t.*,
                   bc.barcode,
                   b.book_id, b.isbn, b.title, b.author,
                   lib.full_name as issued_by_name,
                   DATEDIFF(CURDATE(), t.due_date) as days_overdue
            FROM transactions t
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            JOIN users lib ON t.issued_by = lib.user_id
            WHERE t.user_id = %s AND t.status IN ('active', 'overdue')
            ORDER BY t.due_date ASC
        """
        rows = self.db.execute(query, (user_id,))
        return [self._from_row(row) for row in rows]

    def find_overdue(self, limit: int = 100) -> list[Transaction]:
        """Find all overdue transactions.

        Returns:
            List of overdue Transaction instances.
        """
        query = """

            SELECT t.*,
                   bc.barcode,
                   b.book_id, b.isbn, b.title, b.author,
                   u.full_name as borrower_name, u.username as borrower_username,
                   lib.full_name as issued_by_name,
                   DATEDIFF(CURDATE(), t.due_date) as days_overdue
            FROM transactions t
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            JOIN users lib ON t.issued_by = lib.user_id
            WHERE t.status IN ('active', 'overdue') AND t.due_date < CURDATE()
            ORDER BY t.due_date ASC
            LIMIT %s
        """
        rows = self.db.execute(query, (limit,))
        return [self._from_row(row) for row in rows]

    def find_all_with_details(
        self, limit: int = 100, offset: int = 0, status: TransactionStatus | None = None
    ) -> list[Transaction]:
        """Find all transactions with full details.

        Args:
            limit: Maximum records.
            offset: Records to skip.
            status: Optional status filter.

        Returns:
            List of Transaction instances.
        """
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("t.status = %s")
            params.append(str(status))

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""

            SELECT t.*,
                   bc.barcode,
                   b.book_id, b.isbn, b.title, b.author,
                   u.full_name as borrower_name, u.username as borrower_username,
                   lib.full_name as issued_by_name,
                   ret.full_name as returned_by_name,
                   DATEDIFF(CURDATE(), t.due_date) as days_overdue
            FROM transactions t
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            JOIN users lib ON t.issued_by = lib.user_id
            LEFT JOIN users ret ON t.returned_by = ret.user_id
            WHERE {where_clause}
            ORDER BY t.issue_date DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def create(self, trans_data: TransactionCreate) -> int:
        """Create a new transaction (issue a book).

        Args:
            trans_data: Transaction creation DTO.

        Returns:
            New transaction ID.
        """
        data = {
            "copy_id": trans_data.copy_id,
            "user_id": trans_data.user_id,
            "issued_by": trans_data.issued_by,
            "due_date": trans_data.due_date,
            "status": "active",
        }

        if trans_data.remarks:
            data["remarks"] = trans_data.remarks

        query, params = self._build_insert_query(data)
        return self.db.execute_insert(query, params)

    def return_book(
        self, transaction_id: int, returned_by: int, remarks: str | None = None
    ) -> bool:
        """Mark a transaction as returned.

        Args:
            transaction_id: Transaction ID.
            returned_by: Librarian user ID.
            remarks: Optional remarks.

        Returns:
            True if updated.
        """
        query = """
            UPDATE transactions
            SET return_date = CURRENT_TIMESTAMP,
                returned_by = %s,
                status = 'returned',
                remarks = COALESCE(%s, remarks)
            WHERE transaction_id = %s AND status IN ('active', 'overdue')
        """
        affected = self.db.execute_update(query, (returned_by, remarks, transaction_id))
        return affected > 0

    def mark_overdue(self, transaction_id: int) -> bool:
        """Mark a transaction as overdue.

        Args:
            transaction_id: Transaction ID.

        Returns:
            True if updated.
        """
        query = """
            UPDATE transactions
            SET status = 'overdue'
            WHERE transaction_id = %s AND status = 'active'
        """
        affected = self.db.execute_update(query, (transaction_id,))
        return affected > 0

    def mark_lost(self, transaction_id: int) -> bool:
        """Mark a transaction as lost.

        Args:
            transaction_id: Transaction ID.

        Returns:
            True if updated.
        """
        query = """
            UPDATE transactions
            SET status = 'lost'
            WHERE transaction_id = %s
        """
        affected = self.db.execute_update(query, (transaction_id,))
        return affected > 0

    def count_active_by_user(self, user_id: int) -> int:
        """Count active loans for a user.

        Args:
            user_id: User ID.

        Returns:
            Count of active transactions.
        """
        return self.count("user_id = %s AND status IN ('active', 'overdue')", (user_id,))

    def count_overdue(self) -> int:
        """Count all overdue transactions."""
        query = """
            SELECT COUNT(*) as cnt
            FROM transactions
            WHERE status IN ('active', 'overdue') AND due_date < CURDATE()
        """
        result = self.db.execute_one(query)
        return result["cnt"] if result else 0

    def update_overdue_status(self) -> int:
        """Batch update status of overdue transactions.

        Returns:
            Number of updated transactions.
        """
        query = """
            UPDATE transactions
            SET status = 'overdue'
            WHERE status = 'active' AND due_date < CURDATE()
        """
        return self.db.execute_update(query)

    def delete_by_user(self, user_id: int) -> int:
        """Delete all transactions for a user (borrower).

        Args:
            user_id: User ID.

        Returns:
            Number of deleted transactions.
        """
        query = "DELETE FROM transactions WHERE user_id = %s"
        return self.db.execute_update(query, (user_id,))

    def reassign_issuer(self, old_issuer_id: int, new_issuer_id: int) -> int:
        """Reassign transactions issued by a user to another user.

        Args:
            old_issuer_id: Old issuer (user to be deleted).
            new_issuer_id: New issuer (usually admin).

        Returns:
            Number of updated transactions.
        """
        query = "UPDATE transactions SET issued_by = %s WHERE issued_by = %s"
        return self.db.execute_update(query, (new_issuer_id, old_issuer_id))
