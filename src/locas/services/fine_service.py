"""Fine management service for LOCAS."""

from decimal import Decimal

from locas.config import Config
from locas.core.constants import AuditAction, FineStatus
from locas.core.database import DatabaseManager
from locas.core.exceptions import AuthorizationError, BusinessRuleError, NotFoundError
from locas.core.security import SessionManager
from locas.models.fine import Fine, FineCreate
from locas.repositories.audit_repository import AuditRepository
from locas.repositories.fine_repository import FineRepository
from locas.repositories.transaction_repository import TransactionRepository


class FineService:
    """Handles fine management operations.

    Responsibilities:
    - Fine creation (on overdue returns)
    - Fine payment processing
    - Fine waiver
    - Fine queries

    Attributes:
        config: Application configuration.
        session_manager: Session manager.
        fine_repo: Fine repository.
        trans_repo: Transaction repository.
        audit_repo: Audit repository.
    """

    def __init__(
        self, config: Config, db_manager: DatabaseManager, session_manager: SessionManager
    ) -> None:
        """Initialize FineService.

        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
        """
        self.config = config
        self.session_manager = session_manager
        self.fine_repo = FineRepository(db_manager)
        self.trans_repo = TransactionRepository(db_manager)
        self.audit_repo = AuditRepository(db_manager)

    def _require_librarian(self) -> int:
        """Require librarian role and return current user ID."""
        session = self.session_manager.current_session
        if session is None or not session.has_role("librarian", "admin"):
            raise AuthorizationError("Librarian privileges required")
        return session.user_id

    def _get_current_user_id(self) -> int | None:
        """Get current user ID if authenticated."""
        session = self.session_manager.current_session
        return session.user_id if session else None

    # -------------------------------------------------------------------------
    # Fine Queries
    # -------------------------------------------------------------------------

    def get_fine(self, fine_id: int) -> Fine:
        """Get a fine by ID.

        Args:
            fine_id: Fine ID.

        Returns:
            Fine instance.

        Raises:
            NotFoundError: If fine not found.
        """
        fine = self.fine_repo.find_by_id(fine_id)
        if fine is None:
            raise NotFoundError(f"Fine with ID {fine_id} not found")
        return fine

    def get_fine_by_transaction(self, transaction_id: int) -> Fine | None:
        """Get fine for a transaction.

        Args:
            transaction_id: Transaction ID.

        Returns:
            Fine instance or None.
        """
        return self.fine_repo.find_by_transaction(transaction_id)

    def get_user_fines(
        self, user_id: int, status: FineStatus | None = None, limit: int = 100
    ) -> list[Fine]:
        """Get fines for a user.

        Args:
            user_id: User ID.
            status: Optional status filter.
            limit: Maximum records.

        Returns:
            List of Fine instances.
        """
        return self.fine_repo.find_by_user(user_id, status=status, limit=limit)

    def get_user_pending_fines(self, user_id: int) -> list[Fine]:
        """Get pending fines for a user.

        Args:
            user_id: User ID.

        Returns:
            List of pending Fine instances.
        """
        return self.fine_repo.find_pending_by_user(user_id)

    def get_user_total_pending(self, user_id: int) -> Decimal:
        """Get total pending fine amount for a user.

        Args:
            user_id: User ID.

        Returns:
            Total pending amount.
        """
        return self.fine_repo.get_total_pending_by_user(user_id)

    def list_fines(
        self, status: FineStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Fine]:
        """List all fines.

        Args:
            status: Optional status filter.
            limit: Maximum records.
            offset: Records to skip.

        Returns:
            List of Fine instances.
        """
        return self.fine_repo.find_all_with_details(limit=limit, offset=offset, status=status)

    def list_pending_fines(self, limit: int = 100) -> list[Fine]:
        """List all pending fines.

        Args:
            limit: Maximum records.

        Returns:
            List of pending Fine instances.
        """
        return self.list_fines(status=FineStatus.PENDING, limit=limit)

    # -------------------------------------------------------------------------
    # Fine Operations
    # -------------------------------------------------------------------------

    def create_fine(self, transaction_id: int, user_id: int, amount: Decimal, reason: str) -> Fine:
        """Create a new fine.

        Usually called by TransactionService on return.

        Args:
            transaction_id: Associated transaction.
            user_id: User who owes the fine.
            amount: Fine amount.
            reason: Reason for the fine.

        Returns:
            Created Fine instance.
        """
        fine_data = FineCreate(
            transaction_id=transaction_id, user_id=user_id, amount=amount, reason=reason
        )

        fine_id = self.fine_repo.create(fine_data)
        return self.get_fine(fine_id)

    def calculate_fine(self, days_overdue: int) -> Decimal:
        """Calculate fine amount for given overdue days.

        Args:
            days_overdue: Number of days overdue.

        Returns:
            Fine amount.
        """
        if days_overdue <= 0:
            return Decimal("0")

        return Decimal(str(days_overdue * self.config.fine_rate_per_day))

    def pay_fine(self, fine_id: int) -> Fine:
        """Mark a fine as paid.

        Args:
            fine_id: Fine ID.

        Returns:
            Updated Fine instance.

        Raises:
            AuthorizationError: If not librarian.
            NotFoundError: If fine not found.
            BusinessRuleError: If fine is not pending.
        """
        librarian_id = self._require_librarian()

        fine = self.get_fine(fine_id)

        if fine.status != FineStatus.PENDING:
            raise BusinessRuleError(f"Cannot pay fine with status '{fine.status.display_name}'")

        self.fine_repo.mark_paid(fine_id)

        self.audit_repo.log_action(
            user_id=librarian_id,
            action=AuditAction.FINE_PAID,
            entity_type="fine",
            entity_id=fine_id,
            new_value={"amount": float(fine.amount), "user_id": fine.user_id},
        )

        return self.get_fine(fine_id)

    def waive_fine(self, fine_id: int, reason: str | None = None) -> Fine:
        """Waive a fine.

        Args:
            fine_id: Fine ID.
            reason: Optional reason for waiver.

        Returns:
            Updated Fine instance.

        Raises:
            AuthorizationError: If not admin.
            NotFoundError: If fine not found.
            BusinessRuleError: If fine is not pending.
        """
        session = self.session_manager.current_session
        if session is None or not session.is_admin():
            raise AuthorizationError("Only administrators can waive fines")

        fine = self.get_fine(fine_id)

        if fine.status != FineStatus.PENDING:
            raise BusinessRuleError(f"Cannot waive fine with status '{fine.status.display_name}'")

        self.fine_repo.mark_waived(fine_id)

        self.audit_repo.log_action(
            user_id=session.user_id,
            action=AuditAction.FINE_WAIVED,
            entity_type="fine",
            entity_id=fine_id,
            new_value={"amount": float(fine.amount), "user_id": fine.user_id, "reason": reason},
        )

        return self.get_fine(fine_id)

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_fine_stats(self) -> dict:
        """Get fine statistics.

        Returns:
            Dictionary with statistics.
        """
        return {
            "pending_count": self.fine_repo.count_pending(),
            "pending_total": float(self.fine_repo.get_total_pending()),
        }

    def can_student_borrow(self, user_id: int) -> tuple[bool, str]:
        """Check if a student can borrow based on fines.

        Args:
            user_id: User ID.

        Returns:
            Tuple of (can_borrow, reason).
        """
        pending = self.get_user_total_pending(user_id)
        threshold = Decimal(str(self.config.max_fine_threshold))

        if pending >= threshold:
            return False, f"Pending fines of ₹{pending:.2f} exceed limit of ₹{threshold:.2f}"

        return True, "OK"
