"""Transaction service for LOCAS book issue/return operations."""

from datetime import date
from decimal import Decimal
from typing import Optional

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import (
    NotFoundError, ValidationError, AuthorizationError, BusinessRuleError
)
from locas.core.constants import AuditAction, BookCopyStatus, TransactionStatus
from locas.models.transaction import Transaction, TransactionCreate
from locas.models.book_copy import BookCopy
from locas.repositories.transaction_repository import TransactionRepository
from locas.repositories.copy_repository import CopyRepository
from locas.repositories.book_repository import BookRepository
from locas.repositories.user_repository import UserRepository
from locas.repositories.fine_repository import FineRepository
from locas.repositories.audit_repository import AuditRepository
from locas.utils.date_utils import calculate_due_date, calculate_days_overdue


class TransactionService:
    """Handles book issue and return operations.
    
    Responsibilities:
    - Issue books to students
    - Process book returns
    - Track overdue books
    - Validate borrowing rules
    
    Attributes:
        config: Application configuration.
        session_manager: Session manager.
        trans_repo: Transaction repository.
        copy_repo: Copy repository.
        book_repo: Book repository.
        user_repo: User repository.
        fine_repo: Fine repository.
        audit_repo: Audit repository.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager
    ) -> None:
        """Initialize TransactionService.
        
        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
        """
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.trans_repo = TransactionRepository(db_manager)
        self.copy_repo = CopyRepository(db_manager)
        self.book_repo = BookRepository(db_manager)
        self.user_repo = UserRepository(db_manager)
        self.fine_repo = FineRepository(db_manager)
        self.audit_repo = AuditRepository(db_manager)
    
    def _require_librarian(self) -> int:
        """Require librarian role and return current user ID."""
        session = self.session_manager.current_session
        if session is None or not session.has_role("librarian", "admin"):
            raise AuthorizationError("Librarian privileges required")
        return session.user_id
    
    def _validate_student_can_borrow(self, student_id: int) -> None:
        """Validate that a student can borrow books.
        
        Args:
            student_id: Student user ID.
            
        Raises:
            BusinessRuleError: If student cannot borrow.
        """
        # Check user is active student
        user = self.user_repo.find_by_id(student_id)
        if user is None:
            raise NotFoundError(f"Student with ID {student_id} not found")
        
        if not user.is_active:
            raise BusinessRuleError("Student account is deactivated")
        
        if user.role_name != "student":
            raise BusinessRuleError("Only students can borrow books")
        
        # Check borrow limit
        active_count = self.trans_repo.count_active_by_user(student_id)
        if active_count >= self.config.max_borrow_limit:
            raise BusinessRuleError(
                f"Student has reached the borrowing limit of {self.config.max_borrow_limit} books"
            )
        
        # Check pending fines
        pending_fines = self.fine_repo.get_total_pending_by_user(student_id)
        if pending_fines >= Decimal(str(self.config.max_fine_threshold)):
            raise BusinessRuleError(
                f"Student has pending fines of ₹{pending_fines:.2f}. "
                f"Maximum allowed: ₹{self.config.max_fine_threshold:.2f}"
            )
    
    def _validate_copy_available(self, copy_id: int) -> BookCopy:
        """Validate that a copy is available for issue.
        
        Args:
            copy_id: Copy ID.
            
        Returns:
            BookCopy instance.
            
        Raises:
            NotFoundError: If copy not found.
            BusinessRuleError: If copy not available.
        """
        copy = self.copy_repo.find_by_id(copy_id)
        if copy is None:
            raise NotFoundError(f"Copy with ID {copy_id} not found")
        
        if copy.status != BookCopyStatus.AVAILABLE:
            raise BusinessRuleError(
                f"Copy is not available. Current status: {copy.status.display_name}"
            )
        
        return copy
    
    # -------------------------------------------------------------------------
    # Issue Operations
    # -------------------------------------------------------------------------
    
    def issue_book(
        self,
        copy_id: int,
        student_id: int,
        due_date: Optional[date] = None,
        remarks: Optional[str] = None
    ) -> Transaction:
        """Issue a book to a student.
        
        Args:
            copy_id: Book copy ID to issue.
            student_id: Student user ID.
            due_date: Optional custom due date.
            remarks: Optional remarks.
            
        Returns:
            Created Transaction instance.
            
        Raises:
            AuthorizationError: If not librarian.
            BusinessRuleError: If issue not allowed.
        """
        librarian_id = self._require_librarian()
        
        # Validate student can borrow
        self._validate_student_can_borrow(student_id)
        
        # Validate copy is available
        copy = self._validate_copy_available(copy_id)
        
        # Calculate due date if not provided
        if due_date is None:
            due_date = calculate_due_date(borrow_days=self.config.max_borrow_days)
        
        # Create transaction
        trans_data = TransactionCreate(
            copy_id=copy_id,
            user_id=student_id,
            issued_by=librarian_id,
            due_date=due_date,
            remarks=remarks
        )
        
        transaction_id = self.trans_repo.create(trans_data)
        
        # Update copy status
        self.copy_repo.update_status(copy_id, BookCopyStatus.ISSUED)
        
        # Update book available count
        self.book_repo.update_copy_counts(copy.book_id)
        
        # Log action
        self.audit_repo.log_action(
            user_id=librarian_id,
            action=AuditAction.BOOK_ISSUED,
            entity_type="transaction",
            entity_id=transaction_id,
            new_value={
                "copy_id": copy_id,
                "student_id": student_id,
                "due_date": str(due_date)
            }
        )
        
        return self.get_transaction(transaction_id)
    
    def issue_book_by_barcode(
        self,
        barcode: str,
        student_username: str,
        due_date: Optional[date] = None,
        remarks: Optional[str] = None
    ) -> Transaction:
        """Issue a book using barcode and student username.
        
        Convenience method for the issue workflow.
        
        Args:
            barcode: Copy barcode.
            student_username: Student's username.
            due_date: Optional due date.
            remarks: Optional remarks.
            
        Returns:
            Created Transaction instance.
        """
        # Find copy by barcode
        copy = self.copy_repo.find_by_barcode(barcode)
        if copy is None:
            raise NotFoundError(f"No copy found with barcode '{barcode}'")
        
        # Find student by username
        student = self.user_repo.find_by_username(student_username)
        if student is None:
            raise NotFoundError(f"No student found with username '{student_username}'")
        
        return self.issue_book(
            copy_id=copy.copy_id,
            student_id=student.user_id,
            due_date=due_date,
            remarks=remarks
        )
    
    # -------------------------------------------------------------------------
    # Return Operations
    # -------------------------------------------------------------------------
    
    def return_book(
        self,
        transaction_id: int,
        remarks: Optional[str] = None
    ) -> tuple[Transaction, Optional[Decimal]]:
        """Process a book return.
        
        Args:
            transaction_id: Transaction ID.
            remarks: Optional remarks.
            
        Returns:
            Tuple of (Transaction, fine_amount or None).
            
        Raises:
            AuthorizationError: If not librarian.
            NotFoundError: If transaction not found.
            BusinessRuleError: If already returned.
        """
        librarian_id = self._require_librarian()
        
        # Get transaction
        transaction = self.get_transaction(transaction_id)
        
        if transaction.status == TransactionStatus.RETURNED:
            raise BusinessRuleError("This book has already been returned")
        
        # Calculate fine if overdue
        fine_amount = None
        days_overdue = calculate_days_overdue(transaction.due_date)
        
        if days_overdue > 0:
            fine_amount = Decimal(str(days_overdue * self.config.fine_rate_per_day))
            
            # Create fine record
            from locas.models.fine import FineCreate
            fine_data = FineCreate(
                transaction_id=transaction_id,
                user_id=transaction.user_id,
                amount=fine_amount,
                reason=f"Overdue by {days_overdue} days"
            )
            self.fine_repo.create(fine_data)
        
        # Update transaction
        self.trans_repo.return_book(transaction_id, librarian_id, remarks)
        
        # Update copy status
        self.copy_repo.update_status(transaction.copy_id, BookCopyStatus.AVAILABLE)
        
        # Get copy to update book counts
        copy = self.copy_repo.find_by_id(transaction.copy_id)
        if copy:
            self.book_repo.update_copy_counts(copy.book_id)
        
        # Log action
        self.audit_repo.log_action(
            user_id=librarian_id,
            action=AuditAction.BOOK_RETURNED,
            entity_type="transaction",
            entity_id=transaction_id,
            new_value={
                "days_overdue": days_overdue,
                "fine_amount": float(fine_amount) if fine_amount else None
            }
        )
        
        return self.get_transaction(transaction_id), fine_amount
    
    def return_book_by_barcode(
        self,
        barcode: str,
        remarks: Optional[str] = None
    ) -> tuple[Transaction, Optional[Decimal]]:
        """Return a book using its barcode.
        
        Args:
            barcode: Copy barcode.
            remarks: Optional remarks.
            
        Returns:
            Tuple of (Transaction, fine_amount or None).
        """
        # Find active transaction for this copy
        copy = self.copy_repo.find_by_barcode(barcode)
        if copy is None:
            raise NotFoundError(f"No copy found with barcode '{barcode}'")
        
        transaction = self.trans_repo.find_active_by_copy(copy.copy_id)
        if transaction is None:
            raise BusinessRuleError(f"No active loan found for barcode '{barcode}'")
        
        return self.return_book(transaction.transaction_id, remarks)
    
    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------
    
    def get_transaction(self, transaction_id: int) -> Transaction:
        """Get a transaction by ID.
        
        Args:
            transaction_id: Transaction ID.
            
        Returns:
            Transaction instance.
            
        Raises:
            NotFoundError: If not found.
        """
        transaction = self.trans_repo.find_by_id(transaction_id)
        if transaction is None:
            raise NotFoundError(f"Transaction with ID {transaction_id} not found")
        return transaction
    
    def get_active_transactions(self, limit: int = 100) -> list[Transaction]:
        """Get all active transactions.
        
        Args:
            limit: Maximum records.
            
        Returns:
            List of active Transaction instances.
        """
        return self.trans_repo.find_all_with_details(
            limit=limit,
            status=TransactionStatus.ACTIVE
        )
    
    def get_overdue_transactions(self, limit: int = 100) -> list[Transaction]:
        """Get all overdue transactions.
        
        Args:
            limit: Maximum records.
            
        Returns:
            List of overdue Transaction instances.
        """
        return self.trans_repo.find_overdue(limit=limit)
    
    def get_user_transactions(
        self,
        user_id: int,
        status: Optional[TransactionStatus] = None,
        limit: int = 100
    ) -> list[Transaction]:
        """Get transactions for a user.
        
        Args:
            user_id: User ID.
            status: Optional status filter.
            limit: Maximum records.
            
        Returns:
            List of Transaction instances.
        """
        return self.trans_repo.find_by_user(user_id, status=status, limit=limit)
    
    def get_user_active_transactions(self, user_id: int) -> list[Transaction]:
        """Get active transactions for a user.
        
        Args:
            user_id: User ID.
            
        Returns:
            List of active Transaction instances.
        """
        return self.trans_repo.find_active_by_user(user_id)
    
    # -------------------------------------------------------------------------
    # Maintenance Operations
    # -------------------------------------------------------------------------
    
    def update_overdue_status(self) -> int:
        """Update status of overdue transactions.
        
        Should be called periodically (e.g., daily).
        
        Returns:
            Number of updated transactions.
        """
        return self.trans_repo.update_overdue_status()
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_transaction_stats(self) -> dict:
        """Get transaction statistics.
        
        Returns:
            Dictionary with statistics.
        """
        return {
            "active_transactions": self.trans_repo.count("status = 'active'"),
            "overdue_transactions": self.trans_repo.count_overdue(),
            "total_transactions": self.trans_repo.count(),
        }
