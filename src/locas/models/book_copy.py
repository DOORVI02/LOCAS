"""Book copy data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from locas.core.constants import BookCopyStatus


@dataclass
class BookCopy:
    """Represents a physical copy of a book.
    
    Attributes:
        copy_id: Unique identifier.
        book_id: Foreign key to books table.
        barcode: Unique barcode/copy ID.
        status: Current status of the copy.
        location: Physical location in library.
        added_at: When the copy was added.
        book_title: Title of the book (from join).
        book_author: Author of the book (from join).
    """
    
    copy_id: int
    book_id: int
    barcode: str
    status: BookCopyStatus = BookCopyStatus.AVAILABLE
    location: Optional[str] = None
    added_at: Optional[datetime] = None
    # Joined fields
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    book_isbn: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BookCopy":
        """Create BookCopy from dictionary."""
        status_value = data.get("status", "available")
        if isinstance(status_value, str):
            status = BookCopyStatus(status_value)
        else:
            status = status_value
        
        return cls(
            copy_id=data["copy_id"],
            book_id=data["book_id"],
            barcode=data["barcode"],
            status=status,
            location=data.get("location"),
            added_at=data.get("added_at"),
            book_title=data.get("title") or data.get("book_title"),
            book_author=data.get("author") or data.get("book_author"),
            book_isbn=data.get("isbn") or data.get("book_isbn"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "copy_id": self.copy_id,
            "book_id": self.book_id,
            "barcode": self.barcode,
            "status": str(self.status),
            "location": self.location,
            "added_at": self.added_at,
            "book_title": self.book_title,
            "book_author": self.book_author,
            "book_isbn": self.book_isbn,
        }
    
    @property
    def is_available(self) -> bool:
        """Check if copy is available for issue."""
        return self.status == BookCopyStatus.AVAILABLE
    
    @property
    def is_issued(self) -> bool:
        """Check if copy is currently issued."""
        return self.status == BookCopyStatus.ISSUED


@dataclass
class BookCopyCreate:
    """DTO for creating a new book copy.
    
    Attributes:
        book_id: Book this copy belongs to.
        barcode: Unique barcode.
        location: Physical location.
    """
    
    book_id: int
    barcode: str
    location: Optional[str] = None


@dataclass
class BookCopyUpdate:
    """DTO for updating a book copy.
    
    Attributes:
        status: New status.
        location: New location.
    """
    
    status: Optional[BookCopyStatus] = None
    location: Optional[str] = None
    
    def to_update_dict(self) -> dict[str, Any]:
        """Get dictionary of non-None fields."""
        result = {}
        if self.status is not None:
            result["status"] = str(self.status)
        if self.location is not None:
            result["location"] = self.location
        return result
