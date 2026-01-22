"""Fine repository for database operations."""

from decimal import Decimal
from typing import Any

from locas.core.constants import FineStatus
from locas.models.fine import Fine, FineCreate
from locas.repositories.base_repository import BaseRepository


class FineRepository(BaseRepository[Fine]):
    """Repository for Fine entity operations."""

    @property
    def table_name(self) -> str:
        return "fines"

    @property
    def primary_key(self) -> str:
        return "fine_id"

    def _from_row(self, row: dict[str, Any]) -> Fine:
        return Fine.from_dict(row)

    def find_by_transaction(self, transaction_id: int) -> Fine | None:
        """Find fine for a transaction.

        Args:
            transaction_id: Transaction ID.

        Returns:
            Fine instance or None.
        """
        query = """
            SELECT f.*, u.username, u.full_name
            FROM fines f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.transaction_id = %s
        """
        row = self.db.execute_one(query, (transaction_id,))
        return self._from_row(row) if row else None

    def find_by_user(
        self, user_id: int, status: FineStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Fine]:
        """Find fines for a user.

        Args:
            user_id: User ID.
            status: Optional status filter.
            limit: Maximum records.
            offset: Records to skip.

        Returns:
            List of Fine instances.
        """
        conditions = ["f.user_id = %s"]
        params: list[Any] = [user_id]

        if status:
            conditions.append("f.status = %s")
            params.append(str(status))

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT f.*,
                   t.transaction_id,
                   bc.barcode,
                   b.title
            FROM fines f
            JOIN transactions t ON f.transaction_id = t.transaction_id
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            WHERE {where_clause}
            ORDER BY f.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def find_pending_by_user(self, user_id: int) -> list[Fine]:
        """Find all pending fines for a user.

        Args:
            user_id: User ID.

        Returns:
            List of pending Fine instances.
        """
        return self.find_by_user(user_id, FineStatus.PENDING)

    def find_all_with_details(
        self, limit: int = 100, offset: int = 0, status: FineStatus | None = None
    ) -> list[Fine]:
        """Find all fines with user and book details.

        Args:
            limit: Maximum records.
            offset: Records to skip.
            status: Optional status filter.

        Returns:
            List of Fine instances.
        """
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("f.status = %s")
            params.append(str(status))

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT f.*,
                   u.username, u.full_name,
                   bc.barcode,
                   b.title as book_title
            FROM fines f
            JOIN users u ON f.user_id = u.user_id
            JOIN transactions t ON f.transaction_id = t.transaction_id
            JOIN book_copies bc ON t.copy_id = bc.copy_id
            JOIN books b ON bc.book_id = b.book_id
            WHERE {where_clause}
            ORDER BY f.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def create(self, fine_data: FineCreate) -> int:
        """Create a new fine.

        Args:
            fine_data: Fine creation DTO.

        Returns:
            New fine ID.
        """
        data = {
            "transaction_id": fine_data.transaction_id,
            "user_id": fine_data.user_id,
            "amount": float(fine_data.amount),
            "reason": fine_data.reason,
            "status": "pending",
        }

        query, params = self._build_insert_query(data)
        return self.db.execute_insert(query, params)

    def update_amount(self, fine_id: int, amount: Decimal, reason: str) -> bool:
        """Update fine amount.

        Args:
            fine_id: Fine ID.
            amount: New amount.
            reason: Updated reason.

        Returns:
            True if updated.
        """
        query = """
            UPDATE fines
            SET amount = %s, reason = %s
            WHERE fine_id = %s AND status = 'pending'
        """
        affected = self.db.execute_update(query, (float(amount), reason, fine_id))
        return affected > 0

    def mark_paid(self, fine_id: int) -> bool:
        """Mark a fine as paid.

        Args:
            fine_id: Fine ID.

        Returns:
            True if updated.
        """
        query = """
            UPDATE fines
            SET status = 'paid', paid_at = CURRENT_TIMESTAMP
            WHERE fine_id = %s AND status = 'pending'
        """
        affected = self.db.execute_update(query, (fine_id,))
        return affected > 0

    def mark_waived(self, fine_id: int) -> bool:
        """Waive a fine.

        Args:
            fine_id: Fine ID.

        Returns:
            True if updated.
        """
        query = """
            UPDATE fines
            SET status = 'waived'
            WHERE fine_id = %s AND status = 'pending'
        """
        affected = self.db.execute_update(query, (fine_id,))
        return affected > 0

    def get_total_pending_by_user(self, user_id: int) -> Decimal:
        """Get total pending fines for a user.

        Args:
            user_id: User ID.

        Returns:
            Total pending fine amount.
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM fines
            WHERE user_id = %s AND status = 'pending'
        """
        result = self.db.execute_one(query, (user_id,))
        return Decimal(str(result["total"])) if result else Decimal("0")

    def count_pending(self) -> int:
        """Count all pending fines."""
        return self.count("status = 'pending'")

    def get_total_pending(self) -> Decimal:
        """Get total of all pending fines."""
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM fines
            WHERE status = 'pending'
        """
        result = self.db.execute_one(query)
        return Decimal(str(result["total"])) if result else Decimal("0")

    def delete_by_user(self, user_id: int) -> int:
        """Delete all fines for a user.

        Args:
            user_id: User ID.

        Returns:
            Number of deleted fines.
        """
        query = "DELETE FROM fines WHERE user_id = %s"
        return self.db.execute_update(query, (user_id,))
