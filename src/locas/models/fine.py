"""Fine data models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from locas.core.constants import FineStatus


@dataclass
class Fine:
    """Represents a fine for an overdue book.
    
    Attributes:
        fine_id: Unique identifier.
        transaction_id: Associated transaction.
        user_id: Student who owes the fine.
        amount: Fine amount in currency.
        reason: Reason for the fine.
        status: Current status of the fine.
        created_at: When the fine was created.
        paid_at: When the fine was paid.
    """
    
    fine_id: int
    transaction_id: int
    user_id: int
    amount: Decimal
    reason: str
    status: FineStatus = FineStatus.PENDING
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    # Joined fields
    username: Optional[str] = None
    full_name: Optional[str] = None
    book_title: Optional[str] = None
    barcode: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Fine":
        """Create Fine from dictionary."""
        status_value = data.get("status", "pending")
        if isinstance(status_value, str):
            status = FineStatus(status_value)
        else:
            status = status_value
        
        amount = data["amount"]
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        return cls(
            fine_id=data["fine_id"],
            transaction_id=data["transaction_id"],
            user_id=data["user_id"],
            amount=amount,
            reason=data["reason"],
            status=status,
            created_at=data.get("created_at"),
            paid_at=data.get("paid_at"),
            username=data.get("username"),
            full_name=data.get("full_name"),
            book_title=data.get("title") or data.get("book_title"),
            barcode=data.get("barcode"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fine_id": self.fine_id,
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "amount": float(self.amount),
            "reason": self.reason,
            "status": str(self.status),
            "created_at": self.created_at,
            "paid_at": self.paid_at,
        }
    
    @property
    def is_pending(self) -> bool:
        """Check if fine is still pending."""
        return self.status == FineStatus.PENDING
    
    @property
    def is_paid(self) -> bool:
        """Check if fine has been paid."""
        return self.status == FineStatus.PAID


@dataclass
class FineCreate:
    """DTO for creating a new fine.
    
    Attributes:
        transaction_id: Associated transaction.
        user_id: Student who owes the fine.
        amount: Fine amount.
        reason: Reason for the fine.
    """
    
    transaction_id: int
    user_id: int
    amount: Decimal
    reason: str
