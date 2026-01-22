"""Core utilities for LOCAS."""

from locas.core.database import DatabaseManager
from locas.core.security import SecurityManager
from locas.core.exceptions import (
    LOCASError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    DatabaseError,
    NotFoundError,
    DuplicateError,
    BusinessRuleError,
)
from locas.core.constants import (
    UserRole,
    BookCopyStatus,
    TransactionStatus,
    FineStatus,
    AuditAction,
)

__all__ = [
    # Database
    "DatabaseManager",
    
    # Security
    "SecurityManager",
    
    # Exceptions
    "LOCASError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "DatabaseError",
    "NotFoundError",
    "DuplicateError",
    "BusinessRuleError",
    
    # Constants
    "UserRole",
    "BookCopyStatus",
    "TransactionStatus",
    "FineStatus",
    "AuditAction",
]
