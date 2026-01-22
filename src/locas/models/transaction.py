"""Transaction data models."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from locas.core.constants import TransactionStatus


@dataclass
class Transaction:
    """Represents a book issue/return transaction.
    
    Attributes:
        transaction_id: Unique identifier.
        copy_id: Foreign key to book_copies.
        user_id: Student who borrowed the book.
        issued_by: Librarian who issued the book.
        issue_date: When the book was issued.
        due_date: When the book should be returned.
        return_date: When the book was actually returned.
        returned_by: Librarian who processed the return.
        status: Current status of the transaction.
        remarks: Additional notes.
    """
    
    transaction_id: int
    copy_id: int
    user_id: int
    issued_by: int
    issue_date: datetime
    due_date: date
    return_date: Optional[datetime] = None
    returned_by: Optional[int] = None
    status: TransactionStatus = TransactionStatus.ACTIVE
    remarks: Optional[str] = None
    # Joined fields
    book_id: Optional[int] = None
    book_isbn: Optional[str] = None
    barcode: Optional[str] = None
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    borrower_name: Optional[str] = None
    borrower_username: Optional[str] = None
    issued_by_name: Optional[str] = None
    returned_by_name: Optional[str] = None
    days_overdue: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """Create Transaction from dictionary."""
        status_value = data.get("status", "active")
        if isinstance(status_value, str):
            status = TransactionStatus(status_value)
        else:
            status = status_value
        
        return cls(
            transaction_id=data["transaction_id"],
            copy_id=data["copy_id"],
            user_id=data["user_id"],
            issued_by=data["issued_by"],
            issue_date=data["issue_date"],
            due_date=data["due_date"],
            return_date=data.get("return_date"),
            returned_by=data.get("returned_by"),
            status=status,
            remarks=data.get("remarks"),
            book_id=data.get("book_id"),
            book_isbn=data.get("isbn") or data.get("book_isbn"),
            barcode=data.get("barcode"),
            book_title=data.get("title") or data.get("book_title"),
            book_author=data.get("author") or data.get("book_author"),
            borrower_name=data.get("borrower_name") or data.get("full_name"),
            borrower_username=data.get("borrower_username") or data.get("username"),
            issued_by_name=data.get("issued_by_name") or data.get("issued_by_username"),
            returned_by_name=data.get("returned_by_name"),
            days_overdue=data.get("days_overdue"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "copy_id": self.copy_id,
            "user_id": self.user_id,
            "issued_by": self.issued_by,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "return_date": self.return_date,
            "returned_by": self.returned_by,
            "status": str(self.status),
            "remarks": self.remarks,
            "book_id": self.book_id,
            "book_isbn": self.book_isbn,
            "barcode": self.barcode,
            "book_title": self.book_title,
            "book_author": self.book_author,
            "borrower_name": self.borrower_name,
            "full_name": self.borrower_name,  # Alias for UI compatibility
            "borrower_username": self.borrower_username,
            "username": self.borrower_username,  # Alias for UI compatibility
            "issued_by_name": self.issued_by_name,
            "returned_by_name": self.returned_by_name,
            "days_overdue": self.days_overdue,
        }
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is active (book not returned)."""
        return self.status in (TransactionStatus.ACTIVE, TransactionStatus.OVERDUE)
    
    @property
    def is_overdue(self) -> bool:
        """Check if the book is overdue."""
        if self.return_date is not None:
            return False
        return date.today() > self.due_date
    
    def calculate_days_overdue(self) -> int:
        """Calculate number of days overdue.
        
        Returns:
            Days overdue (0 if not overdue).
        """
        if self.return_date is not None:
            return_dt = self.return_date.date() if isinstance(self.return_date, datetime) else self.return_date
            delta = (return_dt - self.due_date).days
        else:
            delta = (date.today() - self.due_date).days
        
        return max(0, delta)


@dataclass
class TransactionCreate:
    """DTO for creating a new transaction (book issue).
    
    Attributes:
        copy_id: Book copy being issued.
        user_id: Student borrowing the book.
        issued_by: Librarian processing the issue.
        due_date: When the book should be returned.
        remarks: Optional notes.
    """
    
    copy_id: int
    user_id: int
    issued_by: int
    due_date: date
    remarks: Optional[str] = None
