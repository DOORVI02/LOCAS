"""Core utilities for LOCAS."""

from locas.core.constants import (
    AuditAction,
    BookCopyStatus,
    FineStatus,
    TransactionStatus,
    UserRole,
)
from locas.core.database import DatabaseManager
from locas.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    DatabaseError,
    DuplicateError,
    LOCASError,
    NotFoundError,
    ValidationError,
)
from locas.core.security import SecurityManager

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
