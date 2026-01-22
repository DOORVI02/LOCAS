"""Constants and enums for LOCAS."""

from enum import Enum, auto


class UserRole(str, Enum):
    """User role identifiers."""
    
    ADMIN = "admin"
    LIBRARIAN = "librarian"
    STUDENT = "student"
    
    def __str__(self) -> str:
        return self.value


class BookCopyStatus(str, Enum):
    """Status of a physical book copy."""
    
    AVAILABLE = "available"
    ISSUED = "issued"
    LOST = "lost"
    DAMAGED = "damaged"
    RESERVED = "reserved"
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return self.value.title()


class TransactionStatus(str, Enum):
    """Status of a book transaction."""
    
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return self.value.title()


class FineStatus(str, Enum):
    """Status of a fine."""
    
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return self.value.title()


class AuditAction(str, Enum):
    """Types of auditable actions."""
    
    # Authentication
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    
    # User management
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DELETED = "USER_DELETED"
    ROLE_ASSIGNED = "ROLE_ASSIGNED"
    
    # Book management
    BOOK_CREATED = "BOOK_CREATED"
    BOOK_UPDATED = "BOOK_UPDATED"
    BOOK_DELETED = "BOOK_DELETED"
    
    # Copy management
    COPY_ADDED = "COPY_ADDED"
    COPY_UPDATED = "COPY_UPDATED"
    COPY_REMOVED = "COPY_REMOVED"
    COPY_MARKED_LOST = "COPY_MARKED_LOST"
    COPY_MARKED_DAMAGED = "COPY_MARKED_DAMAGED"
    
    # Transactions
    BOOK_ISSUED = "BOOK_ISSUED"
    BOOK_RETURNED = "BOOK_RETURNED"
    
    # Fines
    FINE_CREATED = "FINE_CREATED"
    FINE_PAID = "FINE_PAID"
    FINE_WAIVED = "FINE_WAIVED"
    
    def __str__(self) -> str:
        return self.value


# Application-wide constants
class AppConstants:
    """Application-wide constant values."""
    
    # Date/Time formats
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DISPLAY_DATE_FORMAT = "%d %b %Y"
    DISPLAY_DATETIME_FORMAT = "%d %b %Y %I:%M %p"
    
    # Pagination
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100
    
    # Search
    MIN_SEARCH_LENGTH = 2
    MAX_SEARCH_RESULTS = 500
    
    # Validation
    USERNAME_MIN_LENGTH = 4
    USERNAME_MAX_LENGTH = 50
    EMAIL_MAX_LENGTH = 100
    FULL_NAME_MAX_LENGTH = 100
    ISBN_LENGTH = 13  # ISBN-13
    BARCODE_MAX_LENGTH = 50
    
    # UI
    WINDOW_MIN_WIDTH = 1024
    WINDOW_MIN_HEIGHT = 768
    TABLE_ROW_HEIGHT = 35
