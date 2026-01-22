"""Reporting service for LOCAS."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import AuthorizationError
from locas.repositories.book_repository import BookRepository
from locas.repositories.copy_repository import CopyRepository
from locas.repositories.transaction_repository import TransactionRepository
from locas.repositories.fine_repository import FineRepository
from locas.repositories.user_repository import UserRepository, RoleRepository
from locas.core.constants import BookCopyStatus, TransactionStatus


class ReportService:
    """Handles report generation for LOCAS.
    
    Responsibilities:
    - Generate statistical reports
    - Export report data
    - Dashboard summaries
    
    Attributes:
        config: Application configuration.
        session_manager: Session manager.
        book_repo: Book repository.
        copy_repo: Copy repository.
        trans_repo: Transaction repository.
        fine_repo: Fine repository.
        user_repo: User repository.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager
    ) -> None:
        """Initialize ReportService.
        
        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
        """
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.book_repo = BookRepository(db_manager)
        self.copy_repo = CopyRepository(db_manager)
        self.trans_repo = TransactionRepository(db_manager)
        self.fine_repo = FineRepository(db_manager)
        self.user_repo = UserRepository(db_manager)
        self.role_repo = RoleRepository(db_manager)
    
    def _require_staff(self) -> int:
        """Require librarian or admin role."""
        session = self.session_manager.current_session
        if session is None or not session.has_role("librarian", "admin"):
            raise AuthorizationError("Staff privileges required")
        return session.user_id
    
    # -------------------------------------------------------------------------
    # Dashboard Summaries
    # -------------------------------------------------------------------------
    
    def get_admin_dashboard_stats(self) -> dict[str, Any]:
        """Get statistics for the admin dashboard.
        
        Returns:
            Dictionary with admin dashboard stats.
        """
        session = self.session_manager.current_session
        if session is None or not session.is_admin():
            raise AuthorizationError("Administrator privileges required")
        
        return {
            "total_users": self.user_repo.count(),
            "active_users": self.user_repo.count("is_active = TRUE"),
            "total_books": self.book_repo.count_total(),
            "total_copies": self.copy_repo.count(),
            "available_copies": self.copy_repo.count_by_status(BookCopyStatus.AVAILABLE),
            "issued_copies": self.copy_repo.count_by_status(BookCopyStatus.ISSUED),
            "overdue_transactions": self.trans_repo.count_overdue(),
            "pending_fines_count": self.fine_repo.count_pending(),
            "pending_fines_total": float(self.fine_repo.get_total_pending()),
        }
    
    def get_librarian_dashboard_stats(self) -> dict[str, Any]:
        """Get statistics for the librarian dashboard.
        
        Returns:
            Dictionary with librarian dashboard stats.
        """
        self._require_staff()
        
        return {
            "total_books": self.book_repo.count_total(),
            "available_books": self.book_repo.count_available(),
            "total_copies": self.copy_repo.count(),
            "available_copies": self.copy_repo.count_by_status(BookCopyStatus.AVAILABLE),
            "issued_copies": self.copy_repo.count_by_status(BookCopyStatus.ISSUED),
            "lost_copies": self.copy_repo.count_by_status(BookCopyStatus.LOST),
            "damaged_copies": self.copy_repo.count_by_status(BookCopyStatus.DAMAGED),
            "active_transactions": self.trans_repo.count("status = 'active'"),
            "overdue_transactions": self.trans_repo.count_overdue(),
        }
    
    def get_student_dashboard_stats(self, student_id: int) -> dict[str, Any]:
        """Get statistics for a student's dashboard.
        
        Args:
            student_id: Student user ID.
            
        Returns:
            Dictionary with student dashboard stats.
        """
        return {
            "books_borrowed": self.trans_repo.count_active_by_user(student_id),
            "borrow_limit": self.config.max_borrow_limit,
            "pending_fines": float(self.fine_repo.get_total_pending_by_user(student_id)),
        }
    
    # -------------------------------------------------------------------------
    # Book Reports
    # -------------------------------------------------------------------------
    
    def get_popular_books_report(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most popular books by issue count.
        
        Args:
            limit: Number of books.
            
        Returns:
            List of books with issue counts.
        """
        self._require_staff()
        return self.book_repo.get_popular_books(limit=limit)
    
    def get_book_inventory_report(self) -> dict[str, Any]:
        """Get book inventory summary.
        
        Returns:
            Inventory statistics.
        """
        self._require_staff()
        
        categories = self.book_repo.get_categories()
        category_counts = {}
        
        for category in categories:
            books = self.book_repo.search(category=category, limit=1000)
            category_counts[category] = len(books)
        
        return {
            "total_books": self.book_repo.count_total(),
            "total_copies": self.copy_repo.count(),
            "categories": categories,
            "books_by_category": category_counts,
            "copy_status": {
                "available": self.copy_repo.count_by_status(BookCopyStatus.AVAILABLE),
                "issued": self.copy_repo.count_by_status(BookCopyStatus.ISSUED),
                "lost": self.copy_repo.count_by_status(BookCopyStatus.LOST),
                "damaged": self.copy_repo.count_by_status(BookCopyStatus.DAMAGED),
            }
        }
    
    # -------------------------------------------------------------------------
    # Transaction Reports
    # -------------------------------------------------------------------------
    
    def get_overdue_books_report(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get detailed overdue books report.
        
        Args:
            limit: Maximum records.
            
        Returns:
            List of overdue transactions with details.
        """
        self._require_staff()
        
        overdue = self.trans_repo.find_overdue(limit=limit)
        
        return [
            {
                "transaction_id": t.transaction_id,
                "book_title": t.book_title,
                "barcode": t.barcode,
                "borrower_name": t.borrower_name,
                "borrower_username": t.borrower_username,
                "issue_date": t.issue_date,
                "due_date": t.due_date,
                "days_overdue": t.calculate_days_overdue(),
                "potential_fine": float(
                    t.calculate_days_overdue() * self.config.fine_rate_per_day
                ),
            }
            for t in overdue
        ]
    
    def get_active_loans_report(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get all active loans.
        
        Args:
            limit: Maximum records.
            
        Returns:
            List of active transactions.
        """
        self._require_staff()
        
        active = self.trans_repo.find_all_with_details(
            limit=limit,
            status=TransactionStatus.ACTIVE
        )
        
        return [
            {
                "transaction_id": t.transaction_id,
                "book_title": t.book_title,
                "barcode": t.barcode,
                "borrower_name": t.borrower_name,
                "issue_date": t.issue_date,
                "due_date": t.due_date,
                "issued_by": t.issued_by_name,
            }
            for t in active
        ]
    
    # -------------------------------------------------------------------------
    # User Reports
    # -------------------------------------------------------------------------
    
    def get_active_borrowers_report(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get most active borrowers.
        
        Args:
            limit: Maximum records.
            
        Returns:
            List of users with borrow counts.
        """
        self._require_staff()
        
        # Query to get borrowers ordered by transaction count
        query = """
            SELECT 
                u.user_id,
                u.username,
                u.full_name,
                COUNT(t.transaction_id) as borrow_count,
                SUM(CASE WHEN t.status IN ('active', 'overdue') THEN 1 ELSE 0 END) as active_count
            FROM users u
            JOIN transactions t ON u.user_id = t.user_id
            WHERE u.role_id = (SELECT role_id FROM roles WHERE role_name = 'student')
            GROUP BY u.user_id, u.username, u.full_name
            ORDER BY borrow_count DESC
            LIMIT %s
        """
        
        return self.db_manager.execute(query, (limit,))
    
    def get_users_with_fines_report(self) -> list[dict[str, Any]]:
        """Get users with pending fines.
        
        Returns:
            List of users with fine totals.
        """
        self._require_staff()
        
        query = """
            SELECT 
                u.user_id,
                u.username,
                u.full_name,
                SUM(f.amount) as total_fines,
                COUNT(f.fine_id) as fine_count
            FROM users u
            JOIN fines f ON u.user_id = f.user_id
            WHERE f.status = 'pending'
            GROUP BY u.user_id, u.username, u.full_name
            ORDER BY total_fines DESC
        """
        
        return self.db_manager.execute(query)
    
    # -------------------------------------------------------------------------
    # Fine Reports
    # -------------------------------------------------------------------------
    
    def get_fines_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict[str, Any]:
        """Get fines summary report.
        
        Args:
            start_date: Start of period.
            end_date: End of period.
            
        Returns:
            Fines summary statistics.
        """
        self._require_staff()
        
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        query = """
            SELECT 
                COUNT(*) as total_fines,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status = 'waived' THEN 1 ELSE 0 END) as waived_count,
                SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END) as pending_amount,
                SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) as paid_amount,
                SUM(CASE WHEN status = 'waived' THEN amount ELSE 0 END) as waived_amount
            FROM fines
            WHERE DATE(created_at) BETWEEN %s AND %s
        """
        
        result = self.db_manager.execute_one(query, (start_date, end_date))
        
        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_fines": result["total_fines"] or 0,
            "pending": {
                "count": result["pending_count"] or 0,
                "amount": float(result["pending_amount"] or 0),
            },
            "paid": {
                "count": result["paid_count"] or 0,
                "amount": float(result["paid_amount"] or 0),
            },
            "waived": {
                "count": result["waived_count"] or 0,
                "amount": float(result["waived_amount"] or 0),
            },
        }
    
    # -------------------------------------------------------------------------
    # System Overview
    # -------------------------------------------------------------------------
    
    def get_system_overview(self) -> dict[str, Any]:
        """Get complete system overview.
        
        Returns:
            Comprehensive system statistics.
        """
        self._require_staff()
        
        student_role = self.role_repo.find_by_name("student")
        librarian_role = self.role_repo.find_by_name("librarian")
        
        return {
            "users": {
                "total": self.user_repo.count(),
                "active": self.user_repo.count("is_active = TRUE"),
                "students": self.user_repo.count_by_role(student_role.role_id) if student_role else 0,
                "librarians": self.user_repo.count_by_role(librarian_role.role_id) if librarian_role else 0,
            },
            "books": {
                "total_titles": self.book_repo.count_total(),
                "total_copies": self.copy_repo.count(),
                "available_copies": self.copy_repo.count_by_status(BookCopyStatus.AVAILABLE),
                "issued_copies": self.copy_repo.count_by_status(BookCopyStatus.ISSUED),
            },
            "transactions": {
                "total": self.trans_repo.count(),
                "active": self.trans_repo.count("status = 'active'"),
                "overdue": self.trans_repo.count_overdue(),
            },
            "fines": {
                "pending_count": self.fine_repo.count_pending(),
                "pending_total": float(self.fine_repo.get_total_pending()),
            },
        }
